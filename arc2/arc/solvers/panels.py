"""Rules for inputs that are several panels side by side.

Two families: pick one panel out of the layout, or combine exactly two panels
cell by cell. The *layout* is always a rule (separator colour, or an even split
into k parts), never a per-grid choice — otherwise the fit would be tracking
noise rather than a transformation.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

from arc.dataset import MAX_SYMBOL, Grid, Task
from arc.solver import register
from arc.solvers.base import RuleSolver, Transform
from arc.solvers.grids import background_colour, colour_counts, shape, subgrid

Layout = Callable[[Grid], list[Grid] | None]
Selector = Callable[[list[Grid]], Grid | None]


def _segments(size: int, separators: set[int]) -> list[tuple[int, int]]:
    """Inclusive index ranges between separator lines."""
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for i in range(size):
        if i in separators:
            if start is not None:
                spans.append((start, i - 1))
                start = None
        elif start is None:
            start = i
    if start is not None:
        spans.append((start, size - 1))
    return spans


def _split_on_colour(grid: Grid, colour: int) -> list[Grid] | None:
    rows, cols = shape(grid)
    row_seps = {r for r in range(rows) if all(value == colour for value in grid[r])}
    col_seps = {c for c in range(cols) if all(grid[r][c] == colour for r in range(rows))}
    if not row_seps and not col_seps:
        return None
    row_spans, col_spans = _segments(rows, row_seps), _segments(cols, col_seps)
    if len(row_spans) * len(col_spans) < 2:
        return None
    return [
        subgrid(grid, top, left, bottom, right)
        for top, bottom in row_spans
        for left, right in col_spans
    ]


def _separator_layout(colour: int) -> Layout:
    def layout(grid: Grid) -> list[Grid] | None:
        return _split_on_colour(grid, colour)

    return layout


def _any_separator_layout(grid: Grid) -> list[Grid] | None:
    """Split on whichever colour draws the separator lines, if only one does."""
    found = [
        panels
        for colour in range(MAX_SYMBOL + 1)
        if (panels := _split_on_colour(grid, colour)) is not None
    ]
    return found[0] if len(found) == 1 else None


def _even_layout(axis: str, parts: int) -> Layout:
    def layout(grid: Grid) -> list[Grid] | None:
        rows, cols = shape(grid)
        if axis == "rows":
            if rows % parts:
                return None
            step = rows // parts
            return [subgrid(grid, i * step, 0, i * step + step - 1, cols - 1) for i in range(parts)]
        if cols % parts:
            return None
        step = cols // parts
        return [subgrid(grid, 0, i * step, rows - 1, i * step + step - 1) for i in range(parts)]

    return layout


def layouts() -> Iterator[Layout]:
    """Every panel layout rule the solvers consider, most specific first."""
    yield _any_separator_layout
    for colour in range(MAX_SYMBOL + 1):
        yield _separator_layout(colour)
    for axis in ("rows", "cols"):
        for parts in (2, 3):
            yield _even_layout(axis, parts)


def _by_index(index: int) -> Selector:
    def select(panels: list[Grid]) -> Grid | None:
        if not -len(panels) <= index < len(panels):
            return None
        return panels[index]

    return select


def _odd_one_out(panels: list[Grid]) -> Grid | None:
    """The single panel whose content differs from all the others."""
    odd = [panel for panel in panels if sum(other == panel for other in panels) == 1]
    return odd[0] if len(odd) == 1 and len(panels) > 2 else None


def _most_frequent(panels: list[Grid]) -> Grid | None:
    """The panel content that repeats most often, when that is unambiguous."""
    counts = [(sum(other == panel for other in panels), panel) for panel in panels]
    best = max(count for count, _ in counts)
    winners = [panel for count, panel in counts if count == best]
    return winners[0] if best > 1 and all(w == winners[0] for w in winners) else None


def _by_score(score: Callable[[Grid], int], want_max: bool) -> Selector:
    def select(panels: list[Grid]) -> Grid | None:
        scores = [score(panel) for panel in panels]
        target = max(scores) if want_max else min(scores)
        winners = [panel for panel, value in zip(panels, scores, strict=True) if value == target]
        return winners[0] if len(winners) == 1 else None

    return select


def _ink(panel: Grid) -> int:
    counts = colour_counts(panel)
    return sum(counts.values()) - counts[background_colour(panel)]


def _palette(panel: Grid) -> int:
    return len(colour_counts(panel))


def selectors() -> Iterator[Selector]:
    for index in (0, 1, 2, 3, -1, -2):
        yield _by_index(index)
    yield _odd_one_out
    yield _most_frequent
    for want_max in (True, False):
        yield _by_score(_ink, want_max)
        yield _by_score(_palette, want_max)


def _panel_pick(layout: Layout, select: Selector) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        panels = layout(grid)
        if panels is None:
            return None
        return select(panels)

    return transform


def viable_layouts(task: Task, *, exactly_two: bool = False) -> list[Layout]:
    """Layout rules that split every demonstration input into usable panels.

    Filtering here first keeps the candidate space small: without it each
    selector would re-split every grid, which dominates the running time.
    """
    keep: list[Layout] = []
    for layout in layouts():
        splits = [layout(pair.input) for pair in task.train]
        if not splits or any(panels is None for panels in splits):
            continue
        if exactly_two and any(
            len(panels) != 2 or shape(panels[0]) != shape(panels[1])
            for panels in splits
            if panels is not None
        ):
            continue
        keep.append(layout)
    return keep


@register("panel_select")
class PanelSelectSolver(RuleSolver):
    """The input splits into panels and the output is one of them."""

    name = "panel_select"

    def candidates(self, task: Task) -> Iterable[Transform]:
        for layout in viable_layouts(task):
            for select in selectors():
                yield _panel_pick(layout, select)


_PREDICATES: dict[str, Callable[[bool, bool], bool]] = {
    "and": lambda a, b: a and b,
    "or": lambda a, b: a or b,
    "xor": lambda a, b: a != b,
    "nor": lambda a, b: not (a or b),
    "left_only": lambda a, b: a and not b,
    "right_only": lambda a, b: b and not a,
}


def _panel_logic(
    layout: Layout,
    predicate: Callable[[bool, bool], bool],
    on: int,
    off: int,
    background: int | None,
) -> Transform:
    def transform(grid: Grid) -> Grid | None:
        panels = layout(grid)
        if panels is None or len(panels) != 2 or shape(panels[0]) != shape(panels[1]):
            return None
        left, right = panels
        blank = background_colour(grid) if background is None else background
        return [
            [
                on if predicate(a != blank, b != blank) else off
                for a, b in zip(row_left, row_right, strict=True)
            ]
            for row_left, row_right in zip(left, right, strict=True)
        ]

    return transform


def _output_colours(task: Task) -> list[int]:
    colours: set[int] = set()
    for pair in task.train:
        if pair.output is None:
            return []
        colours.update(value for row in pair.output for value in row)
    return sorted(colours)


@register("panel_logic")
class PanelLogicSolver(RuleSolver):
    """Two panels combined cell by cell with a boolean rule over 'is not background'."""

    name = "panel_logic"

    def candidates(self, task: Task) -> Iterable[Transform]:
        colours = _output_colours(task)
        # More than a handful of output colours means this is not a two-colour
        # mask task, and enumerating pairs would only burn time.
        if not 1 <= len(colours) <= 3:
            return
        for layout in viable_layouts(task, exactly_two=True):
            for predicate in _PREDICATES.values():
                for on in colours:
                    for off in colours:
                        if on == off:
                            continue
                        for background in (None, 0):
                            yield _panel_logic(layout, predicate, on, off, background)
