"""Tests for the offline environment and the action vocabulary."""

from __future__ import annotations

import pytest
from arcengine import GameAction, GameState

from arcagi3.actions import INTERACT, action_from_value, actions_from_values
from arcagi3.mock import CURSOR, TARGET, WALL, Level, MockEnvironment


def test_game_action_cannot_be_built_from_a_bare_int():
    """Guards the quirk actions.py exists to work around.

    GameAction's value map is keyed by (value, action_class), so the obvious
    GameAction(1) raises. If a future SDK release fixes that, this test fails
    and the workaround can go.
    """
    with pytest.raises(ValueError):
        GameAction(1)


def test_action_from_value_round_trips_every_member():
    for action in GameAction:
        assert action_from_value(action.value) is action


def test_action_from_value_rejects_an_unknown_value():
    with pytest.raises(ValueError, match="not a GameAction value"):
        action_from_value(99)


def test_reset_places_the_cursor_at_the_start():
    env = MockEnvironment()
    frame = env.reset()
    assert frame.state is GameState.NOT_FINISHED
    assert frame.full_reset is True
    assert frame.frame[0][0][0] == CURSOR  # level 1 starts at (0, 0)
    assert frame.levels_completed == 0


def test_frame_is_a_stack_of_grids_like_the_real_api():
    frame = MockEnvironment().reset()
    assert isinstance(frame.frame, list)
    assert isinstance(frame.frame[0], list)
    assert isinstance(frame.frame[0][0], list)


def test_available_actions_exclude_moves_off_the_board():
    env = MockEnvironment()
    frame = env.reset()  # cursor at (0, 0): up and left are off-board
    available = set(actions_from_values(frame.available_actions))
    assert GameAction.ACTION1 not in available  # up
    assert GameAction.ACTION3 not in available  # left
    assert GameAction.ACTION2 in available  # down
    assert GameAction.ACTION4 in available  # right


def test_available_actions_exclude_walls():
    level = Level(height=3, width=3, start=(1, 1), target=(0, 0), walls=frozenset({(2, 1)}))
    env = MockEnvironment(levels=(level,))
    frame = env.reset()
    assert GameAction.ACTION2 not in set(actions_from_values(frame.available_actions))


def test_interact_is_offered_only_on_the_target():
    level = Level(height=1, width=2, start=(0, 0), target=(0, 1))
    env = MockEnvironment(levels=(level,))
    frame = env.reset()
    assert INTERACT not in set(actions_from_values(frame.available_actions))
    frame = env.step(GameAction.ACTION4)  # step right, onto the target
    assert INTERACT in set(actions_from_values(frame.available_actions))


def test_interacting_on_the_target_completes_the_level_and_wins():
    level = Level(height=1, width=2, start=(0, 0), target=(0, 1))
    env = MockEnvironment(levels=(level,))
    env.reset()
    env.step(GameAction.ACTION4)
    frame = env.step(INTERACT)
    assert frame.levels_completed == 1
    assert frame.state is GameState.WIN


def test_an_illegal_action_still_costs_a_turn():
    """The real scorecard counts every action, so ignoring availability must hurt."""
    env = MockEnvironment()
    env.reset()
    env.step(GameAction.ACTION1)  # up, off the board from (0, 0)
    assert env.actions_used == 1


def test_walls_and_target_are_drawn_in_the_grid():
    level = Level(height=3, width=3, start=(0, 0), target=(2, 2), walls=frozenset({(1, 1)}))
    grid = MockEnvironment(levels=(level,)).reset().frame[0]
    assert grid[1][1] == WALL
    assert grid[2][2] == TARGET
    assert grid[0][0] == CURSOR


def test_optimal_actions_is_the_walk_plus_one_interact():
    level = Level(height=5, width=5, start=(0, 0), target=(2, 3))
    assert level.optimal_actions == 2 + 3 + 1
    assert MockEnvironment(levels=(level,)).optimal_actions == 6
