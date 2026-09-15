"""Tests for the click-driven environment and the policy that plays it.

Roughly a third of the official games never take a directional input — they are
played almost entirely with MOUSE, and the highest-scoring game in the winner's
run is one of them. This is the second policy family, for those games.
"""

from __future__ import annotations

import pytest
from arcengine import GameAction, GameState

from arcagi3.budget import run_episode
from arcagi3.click_mock import ClickEnvironment, ClickLevel
from arcagi3.clicker import ClickAgent
from arcagi3.sdk_adapter import mouse_action

ONE_LEVEL = (ClickLevel(6, 6, ((3, (0, 0)), (7, (3, 3))), target_colour=7),)


# --- the environment -------------------------------------------------------


def test_clicking_the_right_object_completes_the_level():
    env = ClickEnvironment(levels=ONE_LEVEL)
    env.reset()
    frame = env.step(mouse_action(3, 3))
    assert frame.levels_completed == 1
    assert frame.state is GameState.WIN


def test_clicking_the_wrong_object_costs_a_turn_and_does_nothing():
    env = ClickEnvironment(levels=ONE_LEVEL)
    env.reset()
    frame = env.step(mouse_action(0, 0))
    assert frame.levels_completed == 0
    assert env.actions_used == 1


def test_clicking_empty_space_does_nothing():
    env = ClickEnvironment(levels=ONE_LEVEL)
    env.reset()
    assert env.step(mouse_action(5, 0)).levels_completed == 0


def test_only_reset_and_mouse_are_offered():
    env = ClickEnvironment(levels=ONE_LEVEL)
    frame = env.reset()
    assert set(frame.available_actions) == {GameAction.RESET.value, GameAction.ACTION6.value}


def test_the_baseline_is_one_click_per_level():
    assert ClickEnvironment().optimal_actions == 3


def test_a_finished_game_offers_nothing():
    env = ClickEnvironment(levels=ONE_LEVEL)
    env.reset()
    env.step(mouse_action(3, 3))
    assert env.available_actions() == []


def test_an_environment_needs_at_least_one_level():
    with pytest.raises(ValueError, match="at least one level"):
        ClickEnvironment(levels=())


# --- the policy ------------------------------------------------------------


def test_the_clicker_finishes_the_game():
    result = run_episode(ClickAgent(), ClickEnvironment(), max_actions=100)
    assert result.won
    assert result.levels_completed == result.total_levels


def test_it_learns_which_colour_answers():
    agent = ClickAgent()
    run_episode(agent, ClickEnvironment(), max_actions=100)
    assert agent._responsive[7] > 0
    assert agent._responsive[3] == 0


def test_learning_the_rule_costs_barely_more_than_the_baseline():
    """The layout changes every level; the colour that responds does not."""
    result = run_episode(ClickAgent(), ClickEnvironment(), max_actions=100)
    assert result.actions_used - result.baseline_actions <= 3


def test_play_is_reproducible():
    runs = [run_episode(ClickAgent(), ClickEnvironment(), max_actions=100) for _ in range(3)]
    assert len({r.actions_used for r in runs}) == 1


def test_it_reports_where_its_click_points():
    """The SDK adapter asks a pointing policy for its target."""
    agent = ClickAgent()
    env = ClickEnvironment(levels=ONE_LEVEL)
    frame = env.reset()
    agent.act([frame], frame)
    target = agent.mouse_target()
    assert target is not None
    assert len(target) == 2


def test_it_falls_back_to_reset_when_it_cannot_click():
    agent = ClickAgent()
    env = ClickEnvironment(levels=ONE_LEVEL)
    frame = env.reset()
    stripped = frame.model_copy(update={"available_actions": [GameAction.RESET.value]})
    assert agent.choose_action([stripped], stripped) is GameAction.RESET


def test_an_empty_board_does_not_crash_the_policy():
    agent = ClickAgent()
    env = ClickEnvironment(levels=(ClickLevel(4, 4, (), target_colour=7),))
    frame = env.reset()
    assert agent.choose_action([frame], frame) is GameAction.RESET


def test_a_walking_policy_is_not_used_here():
    """Sanity: the click game offers no directional action at all."""
    frame = ClickEnvironment().reset()
    assert GameAction.ACTION1.value not in frame.available_actions
