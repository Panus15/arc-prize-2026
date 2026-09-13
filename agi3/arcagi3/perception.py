"""Turning a board into objects.

A 64x64 grid of colour indices is a poor thing to reason over directly. The
Milestone #1 winner's agent never saw the raw numbers at all — its prompt says
the grid is "intentionally not exposed" and hands the model a segmentation
instead: 4-connected same-colour objects, their containment and adjacency, and a
position-invariant hash per object for tracking one across frames.

This module builds that view. It is the perception layer every policy here sits
on, whether the policy ends up being a model or a program.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from hashlib import blake2b

Grid = list[list[int]]
Cell = tuple[int, int]

# 4-connectivity: the winner's segmentation uses it, and diagonal joins would
# merge objects that the games treat as separate.
NEIGHBOURS: tuple[Cell, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass(frozen=True)
class Node:
    """One 4-connected region of a single colour."""

    id: int
    colour: int
    cells: frozenset[Cell]
    children: tuple[int, ...] = ()

    @property
    def pixels(self) -> int:
        return len(self.cells)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """(top, left, bottom, right), inclusive."""
        rows = [r for r, _ in self.cells]
        cols = [c for _, c in self.cells]
        return min(rows), min(cols), max(rows), max(cols)

    @property
    def top_left(self) -> Cell:
        top, left, _, _ = self.bbox
        return top, left

    @property
    def shape(self) -> tuple[int, int]:
        top, left, bottom, right = self.bbox
        return bottom - top + 1, right - left + 1

    @property
    def hash(self) -> str:
        """Signature of colour and shape, ignoring position.

        Equal hashes mean the same object wherever it sits, which is what makes
        it usable for tracking an object between frames or spotting duplicates
        within one. Hashed with blake2b rather than hash() because Python salts
        string hashing per process, and these need to compare across runs.
        """
        top, left, _, _ = self.bbox
        offsets = sorted((r - top, c - left) for r, c in self.cells)
        payload = repr((self.colour, offsets)).encode()
        return blake2b(payload, digest_size=8).hexdigest()


@dataclass(frozen=True)
class Segmentation:
    """Every object on a board, plus how they touch and contain each other."""

    nodes: tuple[Node, ...]
    adjacency: tuple[tuple[int, int], ...]
    background: int
    shape: tuple[int, int]

    def by_id(self, node_id: int) -> Node:
        return self.nodes[node_id]

    def of_colour(self, colour: int) -> tuple[Node, ...]:
        return tuple(n for n in self.nodes if n.colour == colour)

    def duplicates(self) -> dict[str, tuple[int, ...]]:
        """Object hashes that appear more than once, mapped to their node ids."""
        groups: dict[str, list[int]] = {}
        for node in self.nodes:
            groups.setdefault(node.hash, []).append(node.id)
        return {h: tuple(ids) for h, ids in groups.items() if len(ids) > 1}

    def neighbours_of(self, node_id: int) -> tuple[int, ...]:
        found = {b if a == node_id else a for a, b in self.adjacency if node_id in (a, b)}
        return tuple(sorted(found))


def background_colour(grid: Grid) -> int:
    """The colour covering the most cells.

    The winner's prompt warns that background is "often white or gray/black-ish"
    but not always, and to verify by area rather than assuming 0. Area is the
    check that is available from a single frame.
    """
    counts = Counter(value for row in grid for value in row)
    # Ties resolve to the lower colour index so the result is deterministic.
    return min(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]


def segment(grid: Grid, *, background: int | None = None) -> Segmentation:
    """Split `grid` into 4-connected same-colour objects, excluding background."""
    if not grid or not grid[0]:
        raise ValueError("cannot segment an empty grid")
    height, width = len(grid), len(grid[0])
    if any(len(row) != width for row in grid):
        raise ValueError("grid is ragged")

    bg = background_colour(grid) if background is None else background
    seen = [[False] * width for _ in range(height)]
    regions: list[tuple[int, frozenset[Cell]]] = []

    # Scan order makes node ids top-most-left-most, matching the winner's spec.
    for r in range(height):
        for c in range(width):
            if seen[r][c] or grid[r][c] == bg:
                continue
            colour = grid[r][c]
            cells = _flood(grid, seen, r, c, colour)
            regions.append((colour, cells))

    cell_owner: dict[Cell, int] = {}
    for index, (_, cells) in enumerate(regions):
        for cell in cells:
            cell_owner[cell] = index

    children = _containment(regions, height, width)
    nodes = tuple(
        Node(id=i, colour=colour, cells=cells, children=children.get(i, ()))
        for i, (colour, cells) in enumerate(regions)
    )
    return Segmentation(
        nodes=nodes,
        adjacency=_adjacency(regions, cell_owner),
        background=bg,
        shape=(height, width),
    )


def _flood(grid: Grid, seen: list[list[bool]], r0: int, c0: int, colour: int) -> frozenset[Cell]:
    height, width = len(grid), len(grid[0])
    queue = deque([(r0, c0)])
    seen[r0][c0] = True
    cells: list[Cell] = []
    while queue:
        r, c = queue.popleft()
        cells.append((r, c))
        for dr, dc in NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if 0 <= nr < height and 0 <= nc < width and not seen[nr][nc] and grid[nr][nc] == colour:
                seen[nr][nc] = True
                queue.append((nr, nc))
    return frozenset(cells)


def _adjacency(
    regions: list[tuple[int, frozenset[Cell]]], owner: dict[Cell, int]
) -> tuple[tuple[int, int], ...]:
    pairs: set[tuple[int, int]] = set()
    for index, (_, cells) in enumerate(regions):
        for r, c in cells:
            for dr, dc in NEIGHBOURS:
                other = owner.get((r + dr, c + dc))
                if other is not None and other != index:
                    pairs.add((min(index, other), max(index, other)))
    return tuple(sorted(pairs))


def _containment(
    regions: list[tuple[int, frozenset[Cell]]], height: int, width: int
) -> dict[int, tuple[int, ...]]:
    """Map each node to the nodes it fully encloses.

    A node is enclosed by `outer` when no 4-connected path reaches outside
    without crossing `outer`. Two prunes keep this cheap on a 64x64 board with
    many objects: only nodes whose bounding box strictly contains another node's
    can enclose anything, and the search stays inside that bounding box —
    `outer` lies entirely within its own box, so escaping the box means escaping
    `outer`.
    """
    boxes = [_bbox_of(cells) for _, cells in regions]
    children: dict[int, list[int]] = {}

    for outer, (_, outer_cells) in enumerate(regions):
        top, left, bottom, right = boxes[outer]
        candidates = [
            i
            for i, (t, ll, b, r) in enumerate(boxes)
            if i != outer and t > top and ll > left and b < bottom and r < right
        ]
        if not candidates:
            continue
        interior = _interior_of(outer_cells, top, left, bottom, right)
        if not interior:
            continue
        for inner in candidates:
            if regions[inner][1] <= interior:
                children.setdefault(outer, []).append(inner)
    return {k: tuple(v) for k, v in children.items()}


def _bbox_of(cells: frozenset[Cell]) -> tuple[int, int, int, int]:
    rows = [r for r, _ in cells]
    cols = [c for _, c in cells]
    return min(rows), min(cols), max(rows), max(cols)


def _interior_of(wall: frozenset[Cell], top: int, left: int, bottom: int, right: int) -> set[Cell]:
    """Cells inside the box that `wall` cuts off from the box border."""
    escaped: set[Cell] = set()
    queue: deque[Cell] = deque()

    def seed(cell: Cell) -> None:
        if cell not in wall and cell not in escaped:
            escaped.add(cell)
            queue.append(cell)

    for r in range(top, bottom + 1):
        seed((r, left))
        seed((r, right))
    for c in range(left, right + 1):
        seed((top, c))
        seed((bottom, c))

    while queue:
        r, c = queue.popleft()
        for dr, dc in NEIGHBOURS:
            nr, nc = r + dr, c + dc
            if top <= nr <= bottom and left <= nc <= right:
                seed((nr, nc))

    box = {(r, c) for r in range(top, bottom + 1) for c in range(left, right + 1)}
    return box - escaped - set(wall)
