"""The fit-then-abstain skeleton every rule solver is built on.

A rule solver proposes candidate transforms, and this base class keeps only one
that reproduces *every* demonstration output exactly. If none does, the solver
returns empty attempts. Abstaining is free, while a guess that happens to be
wrong destroys the one thing these baselines are for: a per-rule coverage
number you can cite without hedging.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from arc.dataset import Grid, Task
from arc.solver import Attempts, trim_attempts

# A fitted rule. Returning None means "this input is outside what I learned" —
# the rule fitted the demonstrations but cannot speak for this particular grid.
Transform = Callable[[Grid], Grid | None]


def explains_train(transform: Transform, task: Task) -> bool:
    """True when `transform` reproduces every demonstration output exactly."""
    if not task.train:
        return False
    for pair in task.train:
        if pair.output is None or transform(pair.input) != pair.output:
            return False
    return True


class RuleSolver:
    """Base class: enumerate candidate transforms, keep one that fits, else abstain."""

    name: str = "rule"

    def candidates(self, task: Task) -> Iterable[Transform]:
        """Yield transforms worth testing against `task`'s demonstrations."""
        raise NotImplementedError

    def fit(self, task: Task) -> Transform | None:
        """The first candidate that explains every train pair, or None."""
        for transform in self.candidates(task):
            if explains_train(transform, task):
                return transform
        return None

    def fits(self, task: Task) -> bool:
        """Whether this rule explains the demonstrations at all."""
        return self.fit(task) is not None

    def solve(self, task: Task) -> list[Attempts]:
        """One attempts list per test input; every list empty when the rule does not fit."""
        transform = self.fit(task)
        if transform is None:
            return [[] for _ in task.test]
        return [attempts_for(transform, pair.input) for pair in task.test]


def attempts_for(transform: Transform, grid: Grid) -> Attempts:
    """Wrap a transform's answer as attempts, abstaining when it declines."""
    out = transform(grid)
    return trim_attempts([out]) if out is not None else []
