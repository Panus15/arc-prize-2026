"""A policy for the games that are played by clicking rather than walking.

Roughly a third of the official games never take a directional input at all —
they are driven almost entirely by MOUSE — so the walking policy has nothing to
offer there. The approach is the same one that works for the controls: try
things, watch what the board does, and keep what paid off.

Here the thing being learned is which objects respond to a click. Objects are
identified by colour, because that is what generalises across levels: the
layout changes every level, the palette usually does not.
"""

from __future__ import annotations

from collections import Counter

from arcengine import FrameData, GameAction

from arcagi3.actions import actions_from_values
from arcagi3.agent import BaseAgent
from arcagi3.perception import Node, segment
from arcagi3.sdk_adapter import mouse_action

Cell = tuple[int, int]


class ClickAgent(BaseAgent):
    """Clicks objects, learns which colours answer, then clicks those."""

    name = "clicker"

    def __init__(self) -> None:
        self._responsive: Counter[int] = Counter()
        self._inert: Counter[int] = Counter()
        self._clicked: set[tuple[int, Cell]] = set()
        self._before: list[list[int]] | None = None
        self._target: Cell | None = None
        self._target_colour: int | None = None
        self._levels_seen = 0

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        board = latest.frame[0]
        self._learn(board, latest.levels_completed)

        available = actions_from_values(latest.available_actions)
        if GameAction.ACTION6 not in available:
            # Nothing to click with; RESET is the only thing that can change that.
            return GameAction.RESET

        choice = self._pick_target(board)
        if choice is None:
            return GameAction.RESET

        cell, colour = choice
        self._before = [row[:] for row in board]
        self._target, self._target_colour = cell, colour
        return mouse_action(*cell)

    def mouse_target(self) -> Cell | None:
        """Where the click just chosen points — read by the SDK adapter."""
        return self._target

    # --- learning ----------------------------------------------------------

    def _learn(self, board: list[list[int]], levels_completed: int) -> None:
        """Credit or blame the colour just clicked for what the board did."""
        if self._before is None or self._target_colour is None:
            return
        colour = self._target_colour
        # Capture the previous board before clearing it: comparing against the
        # cleared field would make every click look like it changed something.
        previous = self._before
        self._before, self._target_colour = None, None

        # A completed level is the strongest possible signal, and it arrives on a
        # board that has already been replaced — so check it before comparing.
        if levels_completed > self._levels_seen:
            self._levels_seen = levels_completed
            self._responsive[colour] += 2
            return
        if board != previous:
            self._responsive[colour] += 1
        else:
            self._inert[colour] += 1

    def _score(self, colour: int) -> int:
        return self._responsive[colour] - self._inert[colour]

    # --- acting ------------------------------------------------------------

    def _pick_target(self, board: list[list[int]]) -> tuple[Cell, int] | None:
        """Where to click next, and the colour of what is being clicked."""
        nodes = segment(board).nodes
        if not nodes:
            return None

        known = [n for n in nodes if self._score(n.colour) > 0]
        if known:
            # A colour that has paid out before is worth clicking again, even
            # somewhere it has not been tried: the layout moves, the rule does not.
            best = max(known, key=lambda n: (self._score(n.colour), -n.top_left[0]))
            return _centre(best), best.colour

        fresh = [n for n in nodes if (n.colour, _centre(n)) not in self._clicked]
        untested = [n for n in fresh if self._score(n.colour) == 0]
        pool = untested or fresh or list(nodes)
        # Ties break by position so that play is reproducible.
        choice = min(pool, key=lambda n: (-self._score(n.colour), n.top_left))
        self._clicked.add((choice.colour, _centre(choice)))
        return _centre(choice), choice.colour


def _centre(node: Node) -> Cell:
    """A cell inside the object, biased to its middle so the click lands on it."""
    top, left, bottom, right = node.bbox
    return (top + bottom) // 2, (left + right) // 2
