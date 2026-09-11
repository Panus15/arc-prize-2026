"""Rules that change grid size by a whole factor: tiling, upscaling, downscaling."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from arc.dataset import MAX_DIM, Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import (
    background_colour,
    flip_horizontal,
    flip_vertical,
    paste_blocks,
    shape,
    solid,
)

# How many times the input repeats, given the input's own shape.
FactorRule = Callable[[int, int], tuple[int, int] | None]


def _constant_factor(kh: int, kw: int) -> FactorRule:
    def rule(rows: int, cols: int) -> tuple[int, int]:
        return kh, kw

    return rule


def _self_factor(rows: int, cols: int) -> tuple[int, int]:
    """Repeat the grid as many times as it is wide and tall (fractal layouts)."""
    return rows, cols


def factor_rules(task: Task, *, shrink: bool = False) -> Iterator[FactorRule]:
    """Yield plausible size-factor rules learned from the demonstration shapes.

    `shrink=True` learns input/output ratios instead of output/input.
    """
    ratios: set[tuple[int, int]] = set()
    for pair in task.train:
        out_shape = pair.output_shape
        if out_shape is None:
            return
        big, small = (pair.input_shape, out_shape) if shrink else (out_shape, pair.input_shape)
        if small[0] == 0 or small[1] == 0 or big[0] % small[0] or big[1] % small[1]:
            ratios.clear()
            break
        ratios.add((big[0] // small[0], big[1] // small[1]))

    if len(ratios) == 1:
        kh, kw = ratios.pop()
        if (kh, kw) != (1, 1):
            yield _constant_factor(kh, kw)
    yield _self_factor


def _too_big(rows: int, cols: int) -> bool:
    """ARC grids top out at 30x30, so anything larger cannot be an answer."""
    return rows > MAX_DIM or cols > MAX_DIM


# (mirror rows, mirror cols, row parity offset, col parity offset)
_MIRROR_MODES: tuple[tuple[bool, bool, int, int], ...] = (
    (False, False, 0, 0),
    (True, False, 0, 0),
    (True, False, 1, 0),
    (False, True, 0, 0),
    (False, True, 0, 1),
    (True, True, 0, 0),
    (True, True, 1, 0),
    (True, True, 0, 1),
    (True, True, 1, 1),
)


def _tiler(
    factor: FactorRule, mirror_rows: bool, mirror_cols: bool, row_off: int, col_off: int
) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        rows, cols = shape(grid)
        size = factor(rows, cols)
        if size is None:
            return None
        kh, kw = size
        if kh < 1 or kw < 1 or (kh, kw) == (1, 1) or _too_big(kh * rows, kw * cols):
            return None
        blocks: list[list[Grid]] = []
        for i in range(kh):
            row_blocks: list[Grid] = []
            for j in range(kw):
                block = grid
                if mirror_rows and (i + row_off) % 2:
                    block = flip_vertical(block)
                if mirror_cols and (j + col_off) % 2:
                    block = flip_horizontal(block)
                row_blocks.append(block)
            blocks.append(row_blocks)
        return paste_blocks(blocks)

    return transform


@register("tiling")
class TilingSolver(RuleSolver):
    """Output is the input repeated k x m times, optionally mirroring alternate copies."""

    name = "tiling"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for factor in factor_rules(task):
            for mirror_rows, mirror_cols, row_off, col_off in _MIRROR_MODES:
                yield _tiler(factor, mirror_rows, mirror_cols, row_off, col_off)


def _fractal(gate_zero: bool, keep_marked: bool, blank_zero: bool) -> Transform:
    """Copy the grid into the blocks its own cells select, blanking the rest."""

    def transform(grid: Grid) -> Grid | None:
        rows, cols = shape(grid)
        if _too_big(rows * rows, cols * cols):
            return None
        # Which colour counts as "empty" is itself a guess: symbol 0 by
        # convention, or whichever colour dominates this particular grid.
        gate = 0 if gate_zero else background_colour(grid)
        blank = solid(rows, cols, 0 if blank_zero else background_colour(grid))
        blocks = [
            [grid if ((value != gate) == keep_marked) else blank for value in grid[r]]
            for r in range(rows)
        ]
        return paste_blocks(blocks)

    return transform


@register("fractal_tile")
class FractalTileSolver(RuleSolver):
    """Self-similar tiling: each cell decides whether its block holds a copy of the grid."""

    name = "fractal_tile"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for gate_zero in (True, False):
            for keep_marked in (True, False):
                for blank_zero in (True, False):
                    yield _fractal(gate_zero, keep_marked, blank_zero)


def _upscaler(factor: FactorRule) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        rows, cols = shape(grid)
        size = factor(rows, cols)
        if size is None:
            return None
        kh, kw = size
        if kh < 1 or kw < 1 or (kh, kw) == (1, 1) or _too_big(kh * rows, kw * cols):
            return None
        out: Grid = []
        for row in grid:
            expanded = [value for value in row for _ in range(kw)]
            out.extend(expanded[:] for _ in range(kh))
        return out

    return transform


@register("upscale")
class UpscaleSolver(RuleSolver):
    """Each input cell becomes a k x m block of the same colour."""

    name = "upscale"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for factor in factor_rules(task):
            yield _upscaler(factor)


def _downscaler(factor: FactorRule) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        rows, cols = shape(grid)
        size = factor(rows, cols)
        if size is None:
            return None
        kh, kw = size
        if kh < 1 or kw < 1 or (kh, kw) == (1, 1) or rows % kh or cols % kw:
            return None
        out: Grid = []
        for r in range(0, rows, kh):
            out_row: list[int] = []
            for c in range(0, cols, kw):
                block = {grid[r + i][c + j] for i in range(kh) for j in range(kw)}
                # A block that is not one flat colour is not a clean reduction.
                if len(block) != 1:
                    return None
                out_row.append(block.pop())
            out.append(out_row)
        return out

    return transform


def _dedupe_runs(grid: Grid) -> Grid:
    """Collapse consecutive duplicate rows and columns to one each."""
    rows = [row for i, row in enumerate(grid) if i == 0 or row != grid[i - 1]]
    keep = [c for c in range(len(rows[0])) if c == 0 or any(row[c] != row[c - 1] for row in rows)]
    return [[row[c] for c in keep] for row in rows]


@register("downscale")
class DownscaleSolver(RuleSolver):
    """Output is a clean block-reduction of the input, or the input with runs collapsed."""

    name = "downscale"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for factor in factor_rules(task, shrink=True):
            yield _downscaler(factor)
        yield _dedupe_runs
