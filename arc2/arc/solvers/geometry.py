"""Whole-grid rigid motions: the eight symmetries of the square, minus identity."""

from __future__ import annotations

from collections.abc import Iterable

from arc.dataset import Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import (
    anti_transpose,
    flip_horizontal,
    flip_vertical,
    rotate90,
    rotate180,
    rotate270,
    transpose,
)

# Identity is excluded on purpose: the `identity` rule owns those tasks, and
# listing it here would double-count them in the coverage table.
OPS: dict[str, Transform] = {
    "rotate180": rotate180,
    "flip_horizontal": flip_horizontal,
    "flip_vertical": flip_vertical,
    "rotate90": rotate90,
    "rotate270": rotate270,
    "transpose": transpose,
    "anti_transpose": anti_transpose,
}


@register("geometry")
class GeometrySolver(RuleSolver):
    """Pick the single rigid motion consistent with every demonstration."""

    name = "geometry"

    def candidates(self, task: Task) -> Iterable[Transform]:
        yield from OPS.values()
