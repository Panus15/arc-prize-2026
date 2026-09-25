"""The walker against a fixed action list — what the real engine actually sends.

`ARCBaseGame` sets `available_actions` once per game and echoes it on every
frame. Our first mock varied it with the player's position, and the navigator
came to depend on that without anyone deciding it should. Replaying recorded
real boards showed the cost: in every game that offers ACTION5 it pressed
ACTION5 on every single turn. These tests hold each repair in place.
"""

from __future__ import annotations

from collections import Counter

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

from arcagi3.budget import run_episode
from arcagi3.mock import MockEnvironment
from arcagi3.navigator import NavigatorAgent, _advanced
from arcagi3.noisy_mock import NoisyEnvironment
from arcagi3.router import walker

SCRAMBLED = {
    GameAction.ACTION1: (0, 1),
    GameAction.ACTION2: (0, -1),
    GameAction.ACTION3: (1, 0),
    GameAction.ACTION4: (-1, 0),
}


def test_a_static_mock_offers_the_same_actions_everywhere():
    env = MockEnvironment(static_actions=True)
    offers = {tuple(env.reset().available_actions)}
    for action in (GameAction.ACTION2, GameAction.ACTION4, GameAction.ACTION1):
        offers.add(tuple(env.step(action).available_actions))
    assert len(offers) == 1
    assert GameAction.ACTION5.value in offers.pop()


def test_an_always_offered_interaction_is_not_pressed_on_sight():
    agent, env = NavigatorAgent(), MockEnvironment(static_actions=True)
    frame = env.reset()
    frames, pressed = [frame], Counter()
    for _ in range(30):
        action = agent.choose_action(frames, frame)
        pressed[action] += 1
        frame = env.step(action)
        frames.append(frame)
    assert pressed[GameAction.ACTION5] <= 3  # it was 30 of 30


def test_an_interaction_that_appears_is_still_taken():
    """The original mock's signal still works: nothing regressed there."""
    assert run_episode(NavigatorAgent(), MockEnvironment(), max_actions=400).won


def test_clicks_are_never_chosen_by_the_walker():
    agent = NavigatorAgent()
    frame = FrameData(
        game_id="t",
        frame=[[[0] * 8 for _ in range(8)]],
        state=GameState.NOT_FINISHED,
        levels_completed=0,
        win_levels=3,
        action_input=ActionInput(id=GameAction.RESET, data={}),
        guid=None,
        full_reset=False,
        available_actions=[1, 2, 3, 4, 5, 6],
    )
    frames = [frame]
    for _ in range(20):
        assert agent.choose_action(frames, frame) is not GameAction.ACTION6


def test_it_wins_with_a_fixed_offer_quiet_or_noisy_or_scrambled():
    arenas = (
        MockEnvironment(static_actions=True),
        MockEnvironment(moves=SCRAMBLED, static_actions=True),
        NoisyEnvironment(static_actions=True),
        NoisyEnvironment(moves=SCRAMBLED, static_actions=True),
    )
    for env in arenas:
        result = run_episode(walker(), env, max_actions=400)
        assert result.won, (type(env).__name__, result)


def test_the_goal_is_not_mistaken_for_a_wall_at_a_level_change():
    agent, env = NavigatorAgent(), MockEnvironment(static_actions=True)
    frame = env.reset()
    frames = [frame]
    while frame.levels_completed == 0:
        frame = env.step(agent.choose_action(frames, frame))
        frames.append(frame)
    agent.choose_action(frames, frame)  # the first look at the new level
    goal_colour = 2
    assert goal_colour not in agent.obstacles.blocked


# --- reading a step from the sprite's edges --------------------------------

P = 4  # sprite colour


def board(*cells: tuple[int, int]) -> list[list[int]]:
    grid = [[0] * 6 for _ in range(3)]
    for r, c in cells:
        grid[r][c] = P
    return grid


def test_a_step_taken_advances_both_edges():
    assert _advanced(board((1, 1)), board((1, 2)), P, (0, 1)) is True


def test_a_flicker_ahead_before_the_step_does_not_hide_it():
    """The trailing frame put the centroid on the destination early."""
    assert _advanced(board((1, 1), (1, 2)), board((1, 2)), P, (0, 1)) is True


def test_a_flicker_beside_a_refused_step_does_not_count_as_moving():
    assert _advanced(board((1, 1)), board((1, 1), (2, 1)), P, (0, 1)) is False


def test_no_sprite_means_no_reading():
    assert _advanced(board(), board((1, 1)), P, (0, 1)) is None
