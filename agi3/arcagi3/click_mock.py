"""An offline stand-in for the click-driven games.

Eight of the 25 official games are never played with a direction — across three
passes each they are almost entirely MOUSE, and one of them, ft09, is the
highest-scoring game in the winner's whole run. A policy that only knows how to
walk cannot touch roughly a third of the field, including its most winnable
game, so those games need an environment to develop against too.

The game here is deliberately plain: several objects on a board, one colour of
which responds to a click. It is not meant to be interesting, it is meant to
have a known optimal action count — one click per level — so that efficiency
is measured rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

Grid = list[list[int]]
Cell = tuple[int, int]

EMPTY = 0
BLOCK = 2  # every object is a BLOCK x BLOCK square


@dataclass(frozen=True)
class ClickLevel:
    """One board: some objects, one of which is the one worth clicking."""

    height: int
    width: int
    objects: tuple[tuple[int, Cell], ...]
    target_colour: int

    def colour_at(self, cell: Cell) -> int | None:
        """The colour of the object covering `cell`, if any."""
        for colour, (top, left) in self.objects:
            if top <= cell[0] < top + BLOCK and left <= cell[1] < left + BLOCK:
                return colour
        return None


LEVELS: tuple[ClickLevel, ...] = (
    ClickLevel(10, 10, ((3, (1, 1)), (7, (1, 6)), (5, (6, 1))), target_colour=7),
    ClickLevel(10, 10, ((7, (6, 6)), (4, (1, 1)), (5, (1, 6))), target_colour=7),
    ClickLevel(12, 12, ((5, (1, 1)), (3, (9, 9)), (7, (5, 5)), (4, (9, 1))), target_colour=7),
)


class ClickEnvironment:
    """A board played entirely by clicking, exposing the same surface as the walker."""

    game_id = "mock-click"

    def __init__(self, levels: tuple[ClickLevel, ...] = LEVELS) -> None:
        if not levels:
            raise ValueError("need at least one level")
        self._levels = levels
        self._index = 0
        self._state = GameState.NOT_PLAYED
        self._actions_used = 0
        self._levels_completed = 0

    @property
    def actions_used(self) -> int:
        return self._actions_used

    @property
    def optimal_actions(self) -> int:
        """One correct click per level is the best any player can do."""
        return len(self._levels)

    @property
    def level(self) -> ClickLevel:
        return self._levels[self._index]

    def reset(self) -> FrameData:
        self._index = 0
        self._state = GameState.NOT_FINISHED
        self._levels_completed = 0
        return self._frame(GameAction.RESET, full_reset=True)

    def step(self, action: GameAction) -> FrameData:
        """Apply a click. A click on the wrong object costs a turn and does nothing."""
        if self._state in (GameState.WIN, GameState.GAME_OVER):
            return self._frame(action)

        self._actions_used += 1
        if action is GameAction.RESET:
            return self._frame(action, full_reset=True)

        if action is GameAction.ACTION6:
            target = self._clicked_cell(action)
            if target is not None and self.level.colour_at(target) == self.level.target_colour:
                self._advance()
        return self._frame(action)

    def available_actions(self) -> list[GameAction]:
        if self._state in (GameState.WIN, GameState.GAME_OVER):
            return []
        return [GameAction.RESET, GameAction.ACTION6]

    # --- internals ----------------------------------------------------------

    @staticmethod
    def _clicked_cell(action: GameAction) -> Cell | None:
        """Where the click landed, read the way the SDK carries it.

        The payload rides on the shared enum member — that is the SDK's own
        contract — and is x/y, where y is the row and x the column.
        """
        data = getattr(action, "action_data", None)
        if data is None:
            return None
        row, col = getattr(data, "y", None), getattr(data, "x", None)
        if row is None or col is None:
            return None
        return int(row), int(col)

    def _advance(self) -> None:
        self._levels_completed += 1
        if self._index + 1 < len(self._levels):
            self._index += 1
        else:
            self._state = GameState.WIN

    def _grid(self) -> Grid:
        level = self.level
        grid = [[EMPTY] * level.width for _ in range(level.height)]
        for colour, (top, left) in level.objects:
            for r in range(top, min(top + BLOCK, level.height)):
                for c in range(left, min(left + BLOCK, level.width)):
                    grid[r][c] = colour
        return grid

    def _frame(self, action: GameAction, *, full_reset: bool = False) -> FrameData:
        return FrameData(
            game_id=self.game_id,
            frame=[self._grid()],
            state=self._state,
            levels_completed=self._levels_completed,
            win_levels=len(self._levels),
            action_input=ActionInput(id=action, data={}),
            guid=None,
            full_reset=full_reset,
            available_actions=[a.value for a in self.available_actions()],
        )
