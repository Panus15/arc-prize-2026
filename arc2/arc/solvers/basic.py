"""The three rules that need no geometry: identity, a constant answer, a colour swap."""

from __future__ import annotations

from collections.abc import Iterable

from arc.dataset import Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import copy_grid


@register("identity")
class IdentitySolver(RuleSolver):
    """Output equals input."""

    name = "identity"

    def candidates(self, task: Task) -> Iterable[Transform]:
        yield copy_grid


@register("constant_output")
class ConstantOutputSolver(RuleSolver):
    """Every demonstration output is the same grid; answer with it."""

    name = "constant_output"

    def candidates(self, task: Task) -> Iterable[Transform]:
        outputs = [pair.output for pair in task.train if pair.output is not None]
        if not outputs or any(out != outputs[0] for out in outputs):
            return
        yield _constant(outputs[0])


def _constant(answer: Grid) -> Transform:
    def transform(grid: Grid) -> Grid:
        return copy_grid(answer)

    return transform


@register("colour_map")
class ColourMapSolver(RuleSolver):
    """Same shape in and out, differing only by a per-colour substitution."""

    name = "colour_map"

    def candidates(self, task: Task) -> Iterable[Transform]:
        mapping: dict[int, int] = {}
        for pair in task.train:
            if pair.output is None or pair.input_shape != pair.output_shape:
                return
            for row_in, row_out in zip(pair.input, pair.output, strict=True):
                for before, after in zip(row_in, row_out, strict=True):
                    if mapping.setdefault(before, after) != after:
                        return
        # A mapping that changes nothing is just `identity`, which already owns
        # those tasks; keeping it here would inflate this rule's coverage.
        if not any(before != after for before, after in mapping.items()):
            return
        yield _substitute(mapping)


def _substitute(mapping: dict[int, int]) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        # An unseen colour has no learned image, and inventing one would be a guess.
        if any(value not in mapping for row in grid for value in row):
            return None
        return [[mapping[value] for value in row] for row in grid]

    return transform
