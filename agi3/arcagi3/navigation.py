"""Routing around things, and working out what counts as a thing to route around.

Walking the two legs of an L gets from A to B on an open board and fails the
moment something sits in the way. Shortest-path search fixes that, but only if
the search knows which cells are walls — and nothing tells an agent that. Colour
8 might be a wall in one game and the floor in the next.

So obstacles are learned the same way the controls are: by trying. A move that
the game refuses — the action was legal, the board did not change — means
whatever occupies the cell ahead blocks movement. A move that succeeds proves
the cell just vacated was passable.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

Grid = list[list[int]]
Cell = tuple[int, int]
Delta = tuple[int, int]

STEPS: tuple[Delta, ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))


@dataclass
class ObstacleModel:
    """Which colours movement has been seen to pass through, and which it has not."""

    blocked: set[int] = field(default_factory=set)
    passable: set[int] = field(default_factory=set)

    def record_blocked(self, colour: int) -> None:
        """A move into this colour was refused."""
        # Evidence of passing through outranks a single refusal: a cell can also
        # refuse entry for reasons that have nothing to do with its colour.
        if colour not in self.passable:
            self.blocked.add(colour)

    def record_passable(self, colour: int) -> None:
        """Movement went through a cell of this colour."""
        self.passable.add(colour)
        self.blocked.discard(colour)

    def is_blocked(self, colour: int) -> bool:
        return colour in self.blocked

    def summary(self) -> str:
        blocked = ",".join(str(c) for c in sorted(self.blocked)) or "-"
        passable = ",".join(str(c) for c in sorted(self.passable)) or "-"
        return f"blocked: {blocked} | passable: {passable}"


def find_path(
    grid: Grid,
    start: Cell,
    goal: Cell,
    obstacles: ObstacleModel | None = None,
) -> list[Delta] | None:
    """Shortest sequence of unit steps from `start` to `goal`, or None.

    The goal cell is always enterable — it is usually occupied by the very thing
    being walked to, and refusing to enter it would make every path fail.
    """
    if not grid or not grid[0]:
        return None
    height, width = len(grid), len(grid[0])
    if not (_inside(start, height, width) and _inside(goal, height, width)):
        return None
    if start == goal:
        return []

    blocked = obstacles or ObstacleModel()
    came_from: dict[Cell, tuple[Cell, Delta]] = {}
    seen = {start}
    queue: deque[Cell] = deque([start])

    while queue:
        cell = queue.popleft()
        for step in STEPS:
            nxt = (cell[0] + step[0], cell[1] + step[1])
            if nxt in seen or not _inside(nxt, height, width):
                continue
            if nxt != goal and blocked.is_blocked(grid[nxt[0]][nxt[1]]):
                continue
            seen.add(nxt)
            came_from[nxt] = (cell, step)
            if nxt == goal:
                return _unwind(came_from, start, goal)
            queue.append(nxt)
    return None


def _unwind(came_from: dict[Cell, tuple[Cell, Delta]], start: Cell, goal: Cell) -> list[Delta]:
    steps: list[Delta] = []
    cell = goal
    while cell != start:
        cell, step = came_from[cell]
        steps.append(step)
    steps.reverse()
    return steps


def _inside(cell: Cell, height: int, width: int) -> bool:
    return 0 <= cell[0] < height and 0 <= cell[1] < width
