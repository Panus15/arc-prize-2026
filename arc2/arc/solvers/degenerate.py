"""The floor: a flat grid of one colour, at a shape learned from the demonstrations.

These rules carry no reasoning at all. They earn their place only because a
measured floor tells you how much of a smarter solver's score is real.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from arc.dataset import Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import (
    background_colour,
    least_common_colour,
    most_common_colour,
    shape,
    solid,
)

ShapeRule = Callable[[Grid], tuple[int, int] | None]
ColourRule = Callable[[Grid], int | None]


def _fixed_shape(rows: int, cols: int) -> ShapeRule:
    def rule(grid: Grid) -> tuple[int, int]:
        return rows, cols

    return rule


def _shape_rules(task: Task) -> Iterator[tuple[str, ShapeRule]]:
    yield "input", shape
    shapes = {pair.output_shape for pair in task.train}
    # The most common output shape is only ever a fit when *every* demonstration
    # shares it — a fitted rule has to reproduce each train output exactly.
    if len(shapes) == 1:
        only = shapes.pop()
        if only is not None:
            yield "fixed", _fixed_shape(*only)


def _fixed_colour(colour: int) -> ColourRule:
    def rule(grid: Grid) -> int:
        return colour

    return rule


def _non_background(pick: Callable[..., int | None]) -> ColourRule:
    def rule(grid: Grid) -> int | None:
        return pick(grid, ignore=background_colour(grid))

    return rule


def _colour_rules(task: Task) -> Iterator[tuple[str, ColourRule]]:
    palettes = {
        colour for pair in task.train if pair.output for row in pair.output for colour in row
    }
    if len(palettes) == 1:
        yield "fixed", _fixed_colour(palettes.pop())
    yield "common", most_common_colour
    yield "most_ink", _non_background(most_common_colour)
    yield "least_ink", _non_background(least_common_colour)


def _filler(shape_rule: ShapeRule, colour_rule: ColourRule) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        size = shape_rule(grid)
        colour = colour_rule(grid)
        if size is None or colour is None:
            return None
        return solid(size[0], size[1], colour)

    return transform


@register("shape_fill")
class ShapeFillSolver(RuleSolver):
    """A single-colour grid: shape from the demonstrations, colour read off the input."""

    name = "shape_fill"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for shape_kind, shape_rule in _shape_rules(task):
            for colour_kind, colour_rule in _colour_rules(task):
                # A fixed shape filled with a fixed colour is just `constant_output`.
                if shape_kind == "fixed" and colour_kind == "fixed":
                    continue
                yield _filler(shape_rule, colour_rule)
