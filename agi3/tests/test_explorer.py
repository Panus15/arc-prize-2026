"""Tests for the action-learning policy.

The claim under test is that the policy works out the controls from what it
observes, rather than relying on the usual ACTION1-is-up layout. Scrambling the
control map is what actually proves that, so it gets its own test.
"""

from __future__ import annotations

import pytest
from arcengine import GameAction

from arcagi3.agent import GreedyAgent
from arcagi3.budget import run_episode
from arcagi3.explorer import ActionModel, ExplorerAgent
from arcagi3.mock import MockEnvironment

# Every direction reassigned: nothing a hard-coded policy assumes still holds.
SCRAMBLED: dict[GameAction, tuple[int, int]] = {
    GameAction.ACTION1: (0, 1),
    GameAction.ACTION2: (0, -1),
    GameAction.ACTION3: (1, 0),
    GameAction.ACTION4: (-1, 0),
}


# --- the action model ------------------------------------------------------


def test_model_records_and_inverts_an_effect():
    model = ActionModel()
    model.record(GameAction.ACTION4, (0, 1), board_changed=True)
    assert model.known(GameAction.ACTION4)
    assert model.action_for((0, 1)) is GameAction.ACTION4


def test_model_marks_an_action_inert_only_when_nothing_moved():
    model = ActionModel()
    model.record(GameAction.ACTION7, None, board_changed=False)
    assert GameAction.ACTION7 in model.inert


def test_an_ambiguous_frame_does_not_overwrite_a_learned_effect():
    """A level change moves everything at once; that is not evidence of inertness."""
    model = ActionModel()
    model.record(GameAction.ACTION1, (-1, 0), board_changed=True)
    model.record(GameAction.ACTION1, None, board_changed=True)
    assert model.effects[GameAction.ACTION1] == (-1, 0)
    assert GameAction.ACTION1 not in model.inert


def test_an_ambiguous_frame_does_not_invent_inertness():
    model = ActionModel()
    model.record(GameAction.ACTION6, None, board_changed=True)
    assert GameAction.ACTION6 not in model.inert


def test_action_for_returns_none_when_no_effect_points_that_way():
    assert ActionModel().action_for((1, 0)) is None


def test_model_normalises_longer_steps_to_a_direction():
    model = ActionModel()
    model.record(GameAction.ACTION2, (3, 0), board_changed=True)
    assert model.action_for((1, 0)) is GameAction.ACTION2


# --- the policy ------------------------------------------------------------


def test_explorer_finishes_the_game():
    result = run_episode(ExplorerAgent())
    assert result.won
    assert result.levels_completed == result.total_levels


def test_explorer_learns_the_standard_control_mapping():
    agent = ExplorerAgent()
    run_episode(agent)
    assert agent.model.effects[GameAction.ACTION1] == (-1, 0)
    assert agent.model.effects[GameAction.ACTION2] == (1, 0)
    assert agent.model.effects[GameAction.ACTION3] == (0, -1)
    assert agent.model.effects[GameAction.ACTION4] == (0, 1)


def test_explorer_learns_what_a_goal_looks_like():
    """Without this it walks to the nearest wall instead of the target."""
    agent = ExplorerAgent()
    run_episode(agent)
    assert agent._goal_colours == {2}


def test_explorer_still_wins_when_the_controls_are_scrambled():
    """The point of learning the controls instead of assuming them."""
    result = run_episode(ExplorerAgent(), MockEnvironment(moves=SCRAMBLED))
    assert result.won
    assert result.levels_completed == result.total_levels


def test_scrambling_costs_the_explorer_nothing():
    standard = run_episode(ExplorerAgent())
    scrambled = run_episode(ExplorerAgent(), MockEnvironment(moves=SCRAMBLED))
    assert scrambled.actions_used == standard.actions_used


def test_a_hard_coded_policy_collapses_on_scrambled_controls():
    """The contrast that gives the previous test its meaning.

    It stumbles through the first level — a straight line, where a wrong turn
    still sometimes lands right — and then never finishes another.
    """
    result = run_episode(GreedyAgent(), MockEnvironment(moves=SCRAMBLED), max_actions=200)
    assert not result.won
    assert result.levels_completed < result.total_levels
    assert result.truncated


def test_play_is_reproducible_across_runs():
    """Guards a real bug: iterating a set of GameAction picked a different

    fallback action in each process, because enum members hash by identity. A
    run whose result changes between processes cannot be reported honestly.
    """
    first = run_episode(GreedyAgent(), MockEnvironment(moves=SCRAMBLED), max_actions=60)
    second = run_episode(GreedyAgent(), MockEnvironment(moves=SCRAMBLED), max_actions=60)
    assert first.levels_completed == second.levels_completed
    assert first.actions_used == second.actions_used


def test_learning_the_controls_costs_only_a_few_actions():
    learned = run_episode(ExplorerAgent())
    perfect = run_episode(GreedyAgent())
    overhead = learned.actions_used - perfect.actions_used
    assert 0 < overhead <= 8, f"probing cost {overhead} extra actions"


def test_explorer_efficiency_stays_well_above_the_random_floor():
    result = run_episode(ExplorerAgent())
    assert result.efficiency is not None
    assert result.efficiency > 0.8


def test_explorer_emits_only_legal_actions():
    """act() raises on an illegal choice, so finishing at all proves this."""
    result = run_episode(ExplorerAgent(), MockEnvironment(moves=SCRAMBLED))
    assert result.won


def test_model_summary_is_readable():
    agent = ExplorerAgent()
    run_episode(agent)
    summary = agent.model.summary()
    assert "UP=" in summary and "RIGHT=" in summary


def test_empty_model_summary_says_so():
    assert ActionModel().summary() == "(nothing learned)"


@pytest.mark.parametrize("seed_moves", [SCRAMBLED, None])
def test_explorer_never_exceeds_the_action_cap(seed_moves):
    env = MockEnvironment(moves=seed_moves) if seed_moves else MockEnvironment()
    result = run_episode(ExplorerAgent(), env, max_actions=100)
    assert result.actions_used <= 100
