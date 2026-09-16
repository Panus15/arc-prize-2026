"""Tests for spending one action budget across several games."""

from __future__ import annotations

from arcagi3.agent import GreedyAgent, RandomAgent
from arcagi3.budgeting import (
    Adaptive,
    EvenSplit,
    GameSpec,
    play_suite,
)
from arcagi3.mock import Level, MockEnvironment
from arcagi3.navigator import NavigatorAgent

# Reachable, but the first level needs 88 actions — far more than a share of a
# tight budget, so it stands in for the games the winner scored zero on.
HARD = (
    Level(
        height=30,
        width=30,
        start=(0, 0),
        target=(0, 29),
        walls=frozenset({(r, 15) for r in range(29)}),
    ),
)


def easy() -> MockEnvironment:
    return MockEnvironment()


def hard() -> MockEnvironment:
    return MockEnvironment(levels=HARD)


def suite(pattern: str = "ehe") -> list[GameSpec]:
    factories = {"e": easy, "h": hard}
    return [
        GameSpec(f"{kind}{index}", factories[kind], NavigatorAgent)
        for index, kind in enumerate(pattern)
    ]


# --- allocation arithmetic -------------------------------------------------


def test_even_split_divides_the_budget():
    assert EvenSplit().allocate(300, 3) == 100


def test_even_split_does_not_strand_a_remainder():
    """Integer division would leave actions unspendable by every game."""
    assert EvenSplit().allocate(100, 3) == 34


def test_allocating_to_no_games_asks_for_nothing():
    assert EvenSplit().allocate(100, 0) == 0
    assert Adaptive().allocate(100, 0) == 0


def test_even_split_never_gives_up_early():
    assert EvenSplit().patience() is None


def test_adaptive_reports_its_patience():
    assert Adaptive(45).patience() == 45


# --- running a suite -------------------------------------------------------


def test_the_budget_is_never_exceeded():
    result = play_suite(suite("ehehe"), EvenSplit(), budget=200)
    assert result.spent <= 200


def test_every_game_appears_in_the_results_even_unplayed_ones():
    """A game the budget never reached still scores zero and must be visible.

    This needs a budget smaller than the number of games: rolling unspent
    actions forward means an even split otherwise reaches everything, however
    thinly.
    """
    games = suite("eeeee")
    result = play_suite(games, EvenSplit(), budget=3)
    assert len(result.outcomes) == len(games)
    assert any(o.allocated == 0 for o in result.outcomes)


def test_rolling_unspent_actions_forward_reaches_every_game():
    games = suite("eeeee")
    result = play_suite(games, EvenSplit(), budget=45)
    assert all(o.allocated > 0 for o in result.outcomes)


def test_each_game_is_played_exactly_once():
    """Competition mode allows one interaction per environment."""
    games = suite("ehe")
    result = play_suite(games, Adaptive(), budget=400)
    assert [o.name for o in result.outcomes] == [g.name for g in games]


def test_a_hopeless_game_is_abandoned_before_its_allocation_runs_out():
    result = play_suite(suite("h"), Adaptive(40), budget=300)
    outcome = result.outcomes[0]
    assert outcome.abandoned
    assert outcome.spent < outcome.allocated


def test_a_game_that_is_winning_is_not_abandoned():
    result = play_suite(suite("e"), Adaptive(40), budget=300)
    assert not result.outcomes[0].abandoned
    assert result.outcomes[0].result.won


def test_zero_budget_plays_nothing():
    result = play_suite(suite("ee"), EvenSplit(), budget=0)
    assert result.spent == 0
    assert result.levels == 0


def test_an_empty_suite_is_handled():
    result = play_suite([], EvenSplit(), budget=100)
    assert result.outcomes == ()
    assert result.levels == 0


def test_allocation_is_reproducible():
    first = play_suite(suite("ehe"), Adaptive(), budget=250)
    second = play_suite(suite("ehe"), Adaptive(), budget=250)
    assert [o.spent for o in first.outcomes] == [o.spent for o in second.outcomes]
    assert first.levels == second.levels


def test_summary_reports_the_totals():
    text = play_suite(suite("ee"), EvenSplit(), budget=200).summary()
    assert "levels" in text and "spent" in text


def test_different_agents_can_be_used_per_game():
    games = [
        GameSpec("greedy-game", easy, GreedyAgent),
        GameSpec("random-game", easy, lambda: RandomAgent(seed=0)),
    ]
    result = play_suite(games, EvenSplit(), budget=200)
    assert result.outcomes[0].result.won


# --- the measured finding --------------------------------------------------


def test_giving_up_early_does_not_beat_an_even_split_here():
    """Measured, and it is a negative result: see docs/budget-allocation.md.

    Abandoning a game only pays if the actions it frees are worth more
    somewhere else. With a policy that either solves a game quickly or not at
    all, the easy games already finish inside their share, so the freed actions
    buy nothing — and too small a patience actively loses levels by cutting off
    games that would have finished.
    """
    games = suite("hehehe")
    even = play_suite(games, EvenSplit(), budget=600)
    impatient = play_suite(games, Adaptive(60), budget=600)
    assert impatient.levels < even.levels


def test_a_generous_patience_at_least_does_no_harm():
    games = suite("hehehe")
    even = play_suite(games, EvenSplit(), budget=600)
    patient = play_suite(games, Adaptive(120), budget=600)
    assert patient.levels == even.levels
