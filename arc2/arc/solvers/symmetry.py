"""Repair a grid whose symmetry has been punched out by an occluding colour.

The rule detects which symmetries the *visible* cells already obey (mirrors,
half turn, diagonals, row/column periods), then propagates colours along the
orbits those symmetries generate. A cell whose orbit holds two different
colours means the assumed symmetry is wrong, so the transform declines instead
of painting over the contradiction.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from arc.dataset import Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import bounding_box, cells, copy_grid, shape, subgrid

# A partial map on cell coordinates; None means "leaves the grid".
CellMap = Callable[[int, int], tuple[int, int] | None]

# A symmetry supported by only a cell or two is coincidence, not structure.
_MIN_AGREEMENTS = 2


def _rigid_maps(rows: int, cols: int) -> Iterator[CellMap]:
    yield lambda r, c: (r, cols - 1 - c)
    yield lambda r, c: (rows - 1 - r, c)
    yield lambda r, c: (rows - 1 - r, cols - 1 - c)
    if rows == cols:
        yield lambda r, c: (c, r)
        yield lambda r, c: (cols - 1 - c, rows - 1 - r)


def _shift(dr: int, dc: int, rows: int, cols: int) -> CellMap:
    def mapping(r: int, c: int) -> tuple[int, int] | None:
        nr, nc = r + dr, c + dc
        return (nr, nc) if 0 <= nr < rows and 0 <= nc < cols else None

    return mapping


def _agrees(grid: Grid, hole: int, mapping: CellMap) -> bool:
    """True when `mapping` never contradicts a visible cell, and confirms a few."""
    agreements = 0
    for r, c, value in cells(grid):
        if value == hole:
            continue
        image = mapping(r, c)
        if image is None:
            continue
        other = grid[image[0]][image[1]]
        if other == hole:
            continue
        if other != value:
            return False
        agreements += 1
    return agreements >= _MIN_AGREEMENTS


def _periods(grid: Grid, hole: int) -> Iterator[CellMap]:
    """The smallest row and column periods the visible cells obey, if any."""
    rows, cols = shape(grid)
    for period in range(1, rows // 2 + 1):
        mapping = _shift(period, 0, rows, cols)
        if _agrees(grid, hole, mapping):
            yield mapping
            break
    for period in range(1, cols // 2 + 1):
        mapping = _shift(0, period, rows, cols)
        if _agrees(grid, hole, mapping):
            yield mapping
            break


def _symmetries(grid: Grid, hole: int) -> list[CellMap]:
    rows, cols = shape(grid)
    found = [mapping for mapping in _rigid_maps(rows, cols) if _agrees(grid, hole, mapping)]
    found.extend(_periods(grid, hole))
    return found


class _Orbits:
    """Union-find over cell indices, one component per symmetry orbit."""

    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, node: int) -> int:
        parent = self._parent
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra


def repair(grid: Grid, hole: int) -> Grid | None:
    """Fill every `hole` cell from its symmetry orbit, or None if that is not possible."""
    rows, cols = shape(grid)
    occluded = [(r, c) for r, c, value in cells(grid) if value == hole]
    if not occluded:
        return None
    symmetries = _symmetries(grid, hole)
    if not symmetries:
        return None

    orbits = _Orbits(rows * cols)
    for r, c, _value in cells(grid):
        for mapping in symmetries:
            image = mapping(r, c)
            if image is not None:
                orbits.union(r * cols + c, image[0] * cols + image[1])

    known: dict[int, int] = {}
    for r, c, value in cells(grid):
        if value == hole:
            continue
        root = orbits.find(r * cols + c)
        if known.setdefault(root, value) != value:
            return None

    out = copy_grid(grid)
    for r, c in occluded:
        colour = known.get(orbits.find(r * cols + c))
        if colour is None:
            return None
        out[r][c] = colour
    return out


def _repair_transform(hole: int, patch_only: bool) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        fixed = repair(grid, hole)
        if fixed is None or not patch_only:
            return fixed
        box = bounding_box(grid, {hole})
        return None if box is None else subgrid(fixed, *box)

    return transform


def hole_colours(task: Task) -> list[int]:
    """Colours that appear in every demonstration input but in none of its outputs."""
    shared: set[int] | None = None
    for pair in task.train:
        if pair.output is None:
            return []
        in_colours = {value for row in pair.input for value in row}
        out_colours = {value for row in pair.output for value in row}
        vanished = in_colours - out_colours
        shared = vanished if shared is None else shared & vanished
    return sorted(shared or ())


@register("symmetry_repair")
class SymmetryRepairSolver(RuleSolver):
    """Restore the masked part of a symmetric grid — whole grid, or just the patch."""

    name = "symmetry_repair"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for hole in hole_colours(task):
            for patch_only in (False, True):
                yield _repair_transform(hole, patch_only)
