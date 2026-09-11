"""Rules whose output is a rectangle cut out of the input."""

from __future__ import annotations

from collections.abc import Iterable

from arc.dataset import MAX_SYMBOL, Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import (
    background_colour,
    bounding_box,
    least_common_colour,
    most_common_colour,
    subgrid,
)


def _crop_to(select: str, background: str) -> Transform:
    """Crop to the bounding box of the cells `select` picks out.

    `background` says how the background is decided: the fixed symbol 0, or the
    input's own most common colour.
    """

    def transform(grid: Grid) -> Grid | None:
        bg = 0 if background == "zero" else background_colour(grid)
        if select == "content":
            keep = {colour for row in grid for colour in row} - {bg}
        else:
            picker = most_common_colour if select == "common" else least_common_colour
            colour = picker(grid, ignore=bg)
            if colour is None:
                return None
            keep = {colour}
        if not keep:
            return None
        box = bounding_box(grid, keep)
        if box is None:
            return None
        return subgrid(grid, *box)

    return transform


def _crop_to_symbol(colour: int) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        box = bounding_box(grid, {colour})
        if box is None:
            return None
        return subgrid(grid, *box)

    return transform


def _trim_border(grid: Grid) -> Grid | None:
    """Drop one ring of cells — the frame some tasks draw around the answer."""
    if len(grid) < 3 or len(grid[0]) < 3:
        return None
    return subgrid(grid, 1, 1, len(grid) - 2, len(grid[0]) - 2)


@register("crop")
class CropSolver(RuleSolver):
    """Output is a sub-rectangle of the input, found by a learned selection rule."""

    name = "crop"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for background in ("zero", "common"):
            for select in ("content", "common", "rare"):
                yield _crop_to(select, background)
        for colour in range(MAX_SYMBOL + 1):
            yield _crop_to_symbol(colour)
        yield _trim_border
