"""Tests for the policy that combines control learning, obstacles and routing."""

from __future__ import annotations

from arcagi3.agent import GreedyAgent
from arcagi3.budget import run_episode
from arcagi3.explorer import ExplorerAgent
from arcagi3.mock import Level, MockEnvironment
from arcagi3.navigator import NavigatorAgent

# A wall sealing column 3 except at the bottom: both legs of an L are blocked,
# so finishing requires routing the long way round.
MAZE = (
    Level(
        height=7,
        width=7,
        start=(0, 0),
        target=(0, 6),
        walls=frozenset({(r, 3) for r in range(6)}),
    ),
)


def maze() -> MockEnvironment:
    return MockEnvironment(levels=MAZE)


def test_baseline_accounts_for_the_detour():
    """Manhattan distance would claim 7 and overstate every efficiency figure."""
    assert MAZE[0].optimal_actions == 19


def test_navigator_finishes_the_standard_levels():
    result = run_episode(NavigatorAgent())
    assert result.won
    assert result.levels_completed == result.total_levels


def test_navigator_solves_a_maze_the_l_shaped_walkers_cannot():
    result = run_episode(NavigatorAgent(), maze(), max_actions=200)
    assert result.won


def test_the_l_shaped_walkers_fail_that_maze():
    """The contrast that justifies the routing."""
    for agent in (GreedyAgent(), ExplorerAgent()):
        result = run_episode(agent, maze(), max_actions=200)
        assert not result.won, f"{agent.name} unexpectedly solved the maze"


def test_navigator_learns_which_colour_is_a_wall():
    agent = NavigatorAgent()
    run_episode(agent, maze(), max_actions=200)
    assert agent.obstacles.is_blocked(8)
    assert not agent.obstacles.is_blocked(0)


def test_navigator_does_not_walk_towards_walls():
    """Walls are objects too; targeting the nearest one stalls the agent."""
    agent = NavigatorAgent()
    result = run_episode(agent, maze(), max_actions=200)
    assert result.won  # it would truncate if it kept routing to the wall


def test_navigator_learns_the_controls_before_committing():
    agent = NavigatorAgent()
    run_episode(agent)
    assert agent.control.confidence() >= 0.65
    assert len(agent.control.mapping()) >= 2


def test_navigator_learns_what_a_goal_looks_like():
    agent = NavigatorAgent()
    run_episode(agent)
    assert 2 in agent._goal_colours


def test_navigator_play_is_reproducible():
    first = run_episode(NavigatorAgent())
    second = run_episode(NavigatorAgent())
    assert first.actions_used == second.actions_used
    assert first.levels_completed == second.levels_completed


def test_robustness_costs_efficiency_on_an_easy_board():
    """Honest trade-off: more samples to become confident, more actions spent."""
    navigator = run_episode(NavigatorAgent())
    explorer = run_episode(ExplorerAgent())
    assert navigator.actions_used > explorer.actions_used
    assert navigator.efficiency is not None and navigator.efficiency > 0.6


def test_a_low_trust_threshold_still_finishes():
    result = run_episode(NavigatorAgent(trust=0.0))
    assert result.won


def test_navigator_emits_only_legal_actions_on_the_maze():
    """act() raises on an illegal choice, so completing the maze proves it."""
    assert run_episode(NavigatorAgent(), maze(), max_actions=200).won
