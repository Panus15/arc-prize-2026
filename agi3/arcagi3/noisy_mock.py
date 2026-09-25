"""An environment with the noise real boards actually have.

Two methods have now looked sound against an offline environment we wrote and
then failed on recorded games: control learning scored 88% here and 0.4% there,
and the click policy's signal turned out to be present on 91-100% of real clicks
and therefore worthless. Both failures have the same cause — the mock was
quieter than reality — so this one reproduces the noise that was measured rather
than inventing a new clean world.

Three properties, each taken from a measurement rather than from imagination:

* A HUD bar that advances every step regardless of the action. The Milestone #1
  winner's own prompt warns that a long strip against an edge is usually a timer
  and that mistaking it for gameplay is a common failure.
* A sprite that changes shape as it moves. On real boards, object-level diffs
  showed 1,040 appearances and 786 disappearances against 992 movements, because
  an animating sprite does not match itself between frames.
* As a consequence of the first two, nearly every action changes the board —
  which is what made "the board changed" useless as a signal in the real click
  games.

A policy that still works here has survived the specific things that broke the
earlier ones. It has still never met a real game.
"""

from __future__ import annotations

from arcengine import FrameData, GameAction

from arcagi3.mock import LEVELS, Level, MockEnvironment

Grid = list[list[int]]

HUD_COLOUR = 6
BLUR_COLOUR = 4  # the same colour as the cursor: a sprite, not a second object


class NoisyEnvironment(MockEnvironment):
    """The walking game, rendered the way a real board renders."""

    game_id = "mock-noisy"

    def __init__(
        self,
        levels: tuple[Level, ...] = LEVELS,
        moves: dict[GameAction, tuple[int, int]] | None = None,
        *,
        hud: bool = True,
        animate: bool = True,
        static_actions: bool = False,
    ) -> None:
        super().__init__(levels=levels, moves=moves, static_actions=static_actions)
        self._hud = hud
        self._animate = animate
        self._ticks = 0

    def step(self, action: GameAction) -> FrameData:
        # The HUD advances on every action, including ones the game refuses, so
        # it cannot be told apart from gameplay by looking at whether it moved.
        self._ticks += 1
        return super().step(action)

    def reset(self) -> FrameData:
        self._ticks = 0
        return super().reset()

    def _grid(self) -> Grid:
        grid = super()._grid()
        if self._animate:
            self._add_motion_blur(grid)
        if self._hud:
            grid.append(self._hud_row(len(grid[0])))
        return grid

    def _add_motion_blur(self, grid: Grid) -> None:
        """Light a cell next to the cursor on alternate steps.

        The cursor is one cell on even steps and two on odd ones, so its shape
        hash differs between consecutive frames — exactly the thing that made
        object matching lose the player on real boards. Only an empty cell is
        used, so the game itself is unchanged.
        """
        if self._ticks % 2 == 0:
            return
        row, col = self._pos
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            r, c = row + dr, col + dc
            if 0 <= r < len(grid) and 0 <= c < len(grid[0]) and grid[r][c] == 0:
                grid[r][c] = BLUR_COLOUR
                return

    def _hud_row(self, width: int) -> list[int]:
        """A bar against the edge that shortens as the run goes on."""
        filled = max(0, width - (self._ticks % (width + 1)))
        return [HUD_COLOUR] * filled + [0] * (width - filled)
