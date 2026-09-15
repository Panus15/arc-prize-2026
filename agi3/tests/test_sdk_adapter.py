"""Tests for the adapter that makes our policies drivable by the competition SDK.

Nothing here talks to a live game. The frames are built by hand from the same
pydantic model the real API returns, so the behaviour under test is the
adapter's, not the network's.
"""

from __future__ import annotations

import pytest
from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

from arcagi3.budget import run_episode
from arcagi3.navigator import NavigatorAgent
from arcagi3.sdk_adapter import (
    BOARD_SIZE,
    SDKPolicyAdapter,
    board_from_frame,
    fallback_action,
    legal_actions,
    mouse_action,
    normalise_frame,
)

MID = [[1, 1], [1, 1]]
SETTLED = [[2, 2], [2, 2]]


def frame(
    stack: list | None = None,
    available: tuple[int, ...] = (1, 2, 3, 4),
    state: GameState = GameState.NOT_FINISHED,
) -> FrameData:
    return FrameData(
        game_id="test",
        frame=stack if stack is not None else [SETTLED],
        state=state,
        levels_completed=0,
        win_levels=3,
        action_input=ActionInput(id=GameAction.RESET, data={}),
        guid=None,
        full_reset=False,
        available_actions=list(available),
    )


# --- reading the frame stack -----------------------------------------------


def test_the_settled_board_is_the_last_layer_not_the_first():
    """`frame` is an animation of one action resolving, not layers of one screen.

    ARCBaseGame.perform_action renders once per engine step while the action is
    still resolving, so index 0 is a mid-animation snapshot and the last entry
    is the board the next action acts on.
    """
    assert board_from_frame(frame([MID, SETTLED])) == SETTLED


def test_a_single_layer_stack_reads_straight_through():
    assert board_from_frame(frame([SETTLED])) == SETTLED


def test_trailing_empty_layers_are_skipped():
    assert board_from_frame(frame([SETTLED, []])) == SETTLED


def test_an_empty_stack_is_a_normal_state_not_an_error():
    """The engine returns frame=[] on WIN and GAME_OVER."""
    assert board_from_frame(frame([])) is None


def test_normalise_collapses_the_stack_so_policies_can_index_zero():
    normalised = normalise_frame(frame([MID, SETTLED]))
    assert normalised.frame == [SETTLED]
    assert normalised.frame[0] == normalised.frame[-1]


def test_normalise_leaves_a_boardless_frame_alone():
    empty = frame([])
    assert normalise_frame(empty).frame == []


def test_normalise_does_not_mutate_the_original():
    original = frame([MID, SETTLED])
    normalise_frame(original)
    assert len(original.frame) == 2


# --- action legality -------------------------------------------------------


def test_available_actions_map_to_enum_members_in_order():
    assert legal_actions(frame(available=(4, 1))) == [GameAction.ACTION4, GameAction.ACTION1]


def test_unknown_action_values_are_dropped_rather_than_raising():
    """A server that adds an action should cost us the option, not the run."""
    assert legal_actions(frame(available=(1, 99))) == [GameAction.ACTION1]


def test_no_available_actions_is_handled():
    assert legal_actions(frame(available=())) == []


def test_fallback_prefers_the_lowest_valued_real_action():
    assert fallback_action([GameAction.ACTION3, GameAction.ACTION1]) is GameAction.ACTION1


def test_fallback_returns_reset_only_when_nothing_else_is_offered():
    assert fallback_action([GameAction.RESET]) is GameAction.RESET
    assert fallback_action([]) is GameAction.RESET


def test_fallback_is_reproducible_across_calls():
    """Iterating a set of GameAction would not be: members hash by identity."""
    options = [GameAction.ACTION4, GameAction.ACTION2, GameAction.ACTION3]
    assert {fallback_action(options) for _ in range(20)} == {GameAction.ACTION2}


# --- the complex action ----------------------------------------------------


def test_mouse_action_maps_row_to_y_and_column_to_x():
    """get_pixels slices frame[y:y+h, x:x+w], so y is the row and x the column."""
    action = mouse_action(9, 5)
    assert action is GameAction.ACTION6
    assert action.action_data.x == 5
    assert action.action_data.y == 9


def test_mouse_action_refuses_a_target_off_the_board():
    """Clamping would spend an action pointed at the wrong cell."""
    with pytest.raises(ValueError, match="outside"):
        mouse_action(BOARD_SIZE, 0)
    with pytest.raises(ValueError, match="outside"):
        mouse_action(0, -1)


# --- the adapter -----------------------------------------------------------


def test_is_done_only_on_a_finished_game():
    adapter = SDKPolicyAdapter()
    assert not adapter.is_done([], frame(state=GameState.NOT_FINISHED))
    assert adapter.is_done([], frame(state=GameState.WIN))
    assert adapter.is_done([], frame(state=GameState.GAME_OVER))


def test_reset_is_the_only_move_before_play_starts():
    adapter = SDKPolicyAdapter()
    assert adapter.choose_action([], frame(state=GameState.NOT_PLAYED)) is GameAction.RESET


def test_a_boardless_frame_does_not_reach_the_policy():
    """Our policies index frame[0] and would raise on an empty stack."""
    adapter = SDKPolicyAdapter()
    chosen = adapter.choose_action([], frame([], available=(2, 3)))
    assert chosen is GameAction.ACTION2


def test_the_choice_is_always_one_the_frame_offered():
    adapter = SDKPolicyAdapter()
    offered = (3,)
    chosen = adapter.choose_action([], frame(available=offered))
    assert chosen.value in offered


def test_a_policy_with_no_mouse_target_is_not_asked_for_one():
    """Policies that never emit ACTION6 need no changes to work here."""
    adapter = SDKPolicyAdapter()
    assert not hasattr(adapter.policy, "mouse_target")
    assert adapter.choose_action([], frame(available=(1, 6))) is not GameAction.ACTION6


def test_a_pointing_policy_supplies_the_click_target():
    class Pointer(NavigatorAgent):
        name = "pointer"

        def choose_action(self, frames, latest):
            return GameAction.ACTION6

        def mouse_target(self):
            return 4, 7

    class Adapter(SDKPolicyAdapter):
        policy_factory = Pointer

    chosen = Adapter().choose_action([], frame(available=(6,)))
    assert chosen is GameAction.ACTION6
    assert (chosen.action_data.y, chosen.action_data.x) == (4, 7)


def test_the_policy_is_built_once_and_reused():
    adapter = SDKPolicyAdapter()
    assert adapter.policy is adapter.policy


# --- end to end ------------------------------------------------------------


def test_a_policy_driven_through_the_adapter_still_finishes_the_game():
    """The adapter must not change how a policy plays on a board it can solve."""
    assert run_episode(NavigatorAgent()).won
