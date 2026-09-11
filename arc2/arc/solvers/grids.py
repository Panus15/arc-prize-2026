"""Grid primitives shared by the rule solvers.

Pure Python on `list[list[int]]`: grids are tiny (30x30 at most) and staying in
the dataset's own representation means every helper's result can be compared to
a task output with `==`, which is exactly the check the rules need.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from arc.dataset import Grid


def shape(grid: Grid) -> tuple[int, int]:
    """Rows and columns of `grid`."""
    return len(grid), len(grid[0])


def copy_grid(grid: Grid) -> Grid:
    """A detached copy, so callers can never mutate a task's own grids."""
    return [row[:] for row in grid]


def solid(rows: int, cols: int, colour: int) -> Grid:
    """A `rows` x `cols` grid of a single colour."""
    return [[colour] * cols for _ in range(rows)]


def cells(grid: Grid) -> Iterator[tuple[int, int, int]]:
    """Yield `(row, col, colour)` for every cell."""
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            yield r, c, value


def transpose(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid, strict=True)]


def flip_horizontal(grid: Grid) -> Grid:
    """Mirror left to right."""
    return [row[::-1] for row in grid]


def flip_vertical(grid: Grid) -> Grid:
    """Mirror top to bottom."""
    return [row[:] for row in grid[::-1]]


def rotate90(grid: Grid) -> Grid:
    """Quarter turn clockwise."""
    return [list(row) for row in zip(*grid[::-1], strict=True)]


def rotate180(grid: Grid) -> Grid:
    return [row[::-1] for row in grid[::-1]]


def rotate270(grid: Grid) -> Grid:
    """Quarter turn counter-clockwise."""
    return [list(row) for row in zip(*grid, strict=True)][::-1]


def anti_transpose(grid: Grid) -> Grid:
    """Reflect in the anti-diagonal."""
    return rotate180(transpose(grid))


def colour_counts(grid: Grid) -> Counter[int]:
    """How often each colour appears."""
    return Counter(value for row in grid for value in row)


def background_colour(grid: Grid) -> int:
    """The most common colour, ties broken by the lowest symbol."""
    counts = colour_counts(grid)
    return min(counts, key=lambda colour: (-counts[colour], colour))


def most_common_colour(grid: Grid, *, ignore: int | None = None) -> int | None:
    """Most common colour, optionally ignoring one; None if nothing is left."""
    counts = colour_counts(grid)
    if ignore is not None:
        counts.pop(ignore, None)
    if not counts:
        return None
    return min(counts, key=lambda colour: (-counts[colour], colour))


def least_common_colour(grid: Grid, *, ignore: int | None = None) -> int | None:
    """Rarest colour, optionally ignoring one; None if nothing is left."""
    counts = colour_counts(grid)
    if ignore is not None:
        counts.pop(ignore, None)
    if not counts:
        return None
    return min(counts, key=lambda colour: (counts[colour], colour))


def bounding_box(grid: Grid, keep: set[int]) -> tuple[int, int, int, int] | None:
    """Inclusive `(top, left, bottom, right)` box around cells whose colour is in `keep`."""
    rows = [r for r, _c, v in cells(grid) if v in keep]
    if not rows:
        return None
    cols = [c for _r, c, v in cells(grid) if v in keep]
    return min(rows), min(cols), max(rows), max(cols)


def subgrid(grid: Grid, top: int, left: int, bottom: int, right: int) -> Grid:
    """The inclusive rectangle `(top, left)`-`(bottom, right)`."""
    return [row[left : right + 1] for row in grid[top : bottom + 1]]


def paste_blocks(blocks: list[list[Grid]]) -> Grid:
    """Join a 2-D arrangement of equally shaped blocks into one grid."""
    out: Grid = []
    for block_row in blocks:
        height = len(block_row[0])
        for r in range(height):
            row: list[int] = []
            for block in block_row:
                row.extend(block[r])
            out.append(row)
    return out
