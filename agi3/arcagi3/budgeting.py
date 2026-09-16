"""Spending a fixed number of actions across many games.

Competition mode scores every environment whether or not it was played, and
allows one interaction with each. So the budget is not really per game — it is
one pool, and every action poured into a game that is going nowhere is an action
some other game never gets. The winner's own run shows why that matters: it
scored zero on 2 of its 25 games, and a hopeless game is not rare.

Two strategies are provided so the question can be settled by measurement rather
than argument: an even split, and an adaptive one that gives up early on games
making no progress and hands what is left to the games still to come.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from arcagi3.agent import BaseAgent
from arcagi3.budget import RunResult, run_episode

# How long a game gets to complete its first level before it is written off.
# Chosen from the recorded runs: the winner's median trial is 138 actions and it
# rarely gets past level 2, so a game that has shown nothing after this long is
# unlikely to turn around.
DEFAULT_PATIENCE = 60


@dataclass(frozen=True)
class GameSpec:
    """One game to play: a name, an environment factory, an agent factory."""

    name: str
    environment: Callable[[], object]
    agent: Callable[[], BaseAgent]


@dataclass(frozen=True)
class GameOutcome:
    """What one game cost and what it returned."""

    name: str
    allocated: int
    result: RunResult
    abandoned: bool

    @property
    def spent(self) -> int:
        return self.result.actions_used

    @property
    def levels(self) -> int:
        return self.result.levels_completed


@dataclass(frozen=True)
class SuiteResult:
    """The whole run across every game."""

    strategy: str
    budget: int
    outcomes: tuple[GameOutcome, ...]

    @property
    def levels(self) -> int:
        return sum(o.levels for o in self.outcomes)

    @property
    def spent(self) -> int:
        return sum(o.spent for o in self.outcomes)

    @property
    def games_won(self) -> int:
        return sum(1 for o in self.outcomes if o.result.won)

    @property
    def abandoned(self) -> int:
        return sum(1 for o in self.outcomes if o.abandoned)

    def summary(self) -> str:
        return (
            f"{self.strategy:<10} levels {self.levels:>3}  won {self.games_won:>2}/"
            f"{len(self.outcomes):<3} spent {self.spent:>4}/{self.budget:<4} "
            f"abandoned {self.abandoned}"
        )


class Strategy(Protocol):
    """Decides how many actions the next game gets."""

    name: str

    def allocate(self, remaining_budget: int, games_left: int) -> int:
        """Actions to give the next game."""

    def patience(self) -> int | None:
        """Actions a game gets to show progress, or None to never give up early."""


class EvenSplit:
    """Every game gets the same share, and plays it out. The honest baseline."""

    name = "even"

    def allocate(self, remaining_budget: int, games_left: int) -> int:
        if games_left <= 0:
            return 0
        # Integer division would strand the remainder; rounding up lets earlier
        # games use it, and later games are still bounded by what is left.
        return -(-remaining_budget // games_left)

    def patience(self) -> int | None:
        return None


class Adaptive:
    """Cuts losses on games showing nothing, and rolls the rest forward."""

    name = "adaptive"

    def __init__(self, patience_actions: int = DEFAULT_PATIENCE) -> None:
        self._patience = patience_actions

    def allocate(self, remaining_budget: int, games_left: int) -> int:
        if games_left <= 0:
            return 0
        return -(-remaining_budget // games_left)

    def patience(self) -> int | None:
        return self._patience


def play_suite(
    games: Sequence[GameSpec],
    strategy: Strategy,
    budget: int,
) -> SuiteResult:
    """Play every game in order under `strategy`, within one shared budget.

    Games are played once each and never resumed, matching the competition's
    one-interaction rule. Unspent actions roll forward, which is the whole point
    of abandoning early: what a hopeless game does not spend, a later one can.
    """
    remaining = max(0, budget)
    outcomes: list[GameOutcome] = []

    for index, spec in enumerate(games):
        games_left = len(games) - index
        allocated = min(strategy.allocate(remaining, games_left), remaining)
        if allocated <= 0:
            outcomes.append(_unplayed(spec, remaining))
            continue

        patience = strategy.patience()
        stop = _patience_check(patience) if patience is not None else None
        result = run_episode(
            spec.agent(),
            spec.environment(),  # type: ignore[arg-type]
            max_actions=allocated,
            should_stop=stop,
        )
        remaining -= result.actions_used
        outcomes.append(
            GameOutcome(
                name=spec.name,
                allocated=allocated,
                result=result,
                abandoned=bool(
                    patience is not None and not result.won and result.actions_used < allocated
                ),
            )
        )

    return SuiteResult(strategy=strategy.name, budget=budget, outcomes=tuple(outcomes))


def _patience_check(patience: int) -> Callable[[int, int], bool]:
    """Give up once `patience` actions have produced no completed level."""

    def should_stop(actions_used: int, levels_completed: int) -> bool:
        return levels_completed == 0 and actions_used >= patience

    return should_stop


def _unplayed(spec: GameSpec, remaining: int) -> GameOutcome:
    """A game the budget never reached still has to appear in the results."""
    empty = run_episode(spec.agent(), spec.environment(), max_actions=0)  # type: ignore[arg-type]
    return GameOutcome(name=spec.name, allocated=0, result=empty, abandoned=remaining <= 0)
