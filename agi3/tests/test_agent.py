"""Tests for the agent base, reference policies and budget accounting."""

from __future__ import annotations

import pytest
from arcengine import GameAction, GameState

from arcagi3.agent import BaseAgent, GreedyAgent, IllegalActionError, RandomAgent
from arcagi3.budget import run_episode
from arcagi3.mock import Level, MockEnvironment

ONE_STEP = (Level(height=1, width=2, start=(0, 0), target=(0, 1)),)


class AlwaysUp(BaseAgent):
    """Returns a move that is illegal from the starting corner."""

    name = "always_up"

    def choose_action(self, frames, latest):
        return GameAction.ACTION1


def test_illegal_action_is_rejected_loudly():
    env = MockEnvironment()
    frame = env.reset()
    with pytest.raises(IllegalActionError, match="always_up chose ACTION1"):
        AlwaysUp().act([frame], frame)


def test_greedy_finishes_at_the_baseline_action_count():
    result = run_episode(GreedyAgent())
    assert result.won
    assert result.levels_completed == result.total_levels
    assert result.actions_used == result.baseline_actions
    assert result.efficiency == pytest.approx(1.0)


def test_random_agent_only_emits_legal_actions():
    """It may waste actions, but never illegal ones — act() would raise."""
    result = run_episode(RandomAgent(seed=7), max_actions=200)
    assert result.actions_used <= 200


def test_random_agent_is_deterministic_for_a_seed():
    a = run_episode(RandomAgent(seed=3), max_actions=120)
    b = run_episode(RandomAgent(seed=3), max_actions=120)
    assert a.actions_used == b.actions_used
    assert a.levels_completed == b.levels_completed


def test_episode_truncates_rather_than_looping_forever():
    class Stuck(BaseAgent):
        name = "stuck"

        def choose_action(self, frames, latest):
            return GameAction.RESET

    result = run_episode(Stuck(), max_actions=25)
    assert result.truncated
    assert not result.won
    assert result.actions_used == 25


def test_is_done_stops_on_a_win():
    result = run_episode(GreedyAgent(), MockEnvironment(levels=ONE_STEP))
    assert result.state is GameState.WIN
    assert result.actions_used == 2  # one step, one interact


def test_efficiency_is_none_when_no_action_was_taken():
    class Immediate(BaseAgent):
        name = "immediate"

        def is_done(self, frames, latest):
            return True

        def choose_action(self, frames, latest):  # pragma: no cover - never called
            raise AssertionError("should not be asked for an action")

    assert run_episode(Immediate()).efficiency is None


def test_summary_mentions_the_outcome_and_the_baseline():
    text = run_episode(GreedyAgent()).summary()
    assert "WIN" in text and "baseline" in text
