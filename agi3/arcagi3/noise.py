"""Add measured board noise to any ARC-AGI-3 environment.

An agent that clears every level of the environment its authors wrote has shown
very little. This project has four measurements of that: methods convincing in
a quiet simulator scored 0.4% on real boards, learned nothing from a signal that
fires on 91-100% of real clicks, cleared no levels once noise was added, and —
most pointedly — a method that won decisively on a mock calibrated from real
statistics was the worse of the two on real boards.

`NoisyEnvironment` applies this to our own game. This module applies it to
anyone's. Wrap an environment that returns `FrameData` and its frames come back
carrying the noise real boards carry, with each property switchable so a failure
can be attributed to one of them rather than to "noise" in general.

    from arcagi3.noise import NoiseWrapper

    noisy = NoiseWrapper(MyEnvironment())
    frame = noisy.reset()
    frame = noisy.step(action)      # same surface, noisier frames

What it reproduces, and the measurement behind each:

* A HUD strip against an edge that advances on every action, including ones the
  game refuses. The Milestone #1 winner's prompt warns that a strip against a
  border is usually a timer and that mistaking it for gameplay is a common
  failure; making it advance regardless of the action is what stops it being
  separable by "did it move?".
* A sprite that changes shape as it moves. Object-level diffs of real play
  showed 1,040 appearances and 786 disappearances against 992 movements,
  because an animating sprite does not match itself between frames.
* As a consequence, a board that changes on essentially every action — which is
  what made "the board changed" worthless as a learning signal in real games.

Name `sprite_colour` to make it a hard test. Measured on our own walking game,
only one of these properties breaks a learning policy, and it is a narrow one:

    animating the controlled object only      policy clears 0 of 3 levels
    animating every small object              policy clears 3 of 3
    animating only the goal                   policy clears 3 of 3
    HUD alone, nothing animated               policy clears 3 of 3
    controlled object animated, no HUD        policy clears 0 of 3

So it is not noise that defeats control learning, but noise on the very signal
being learned from. Noise elsewhere — even a great deal of it — costs nothing.
Left to itself this wrapper animates every small object, which is realistic and
easy; naming the object under control is what reproduces the failure.

It is a test, not a simulator. Passing it means a method survived the specific
things that broke ours; it does not mean the method will survive a real game.
Our own measurements say to expect another gap there.
"""

from __future__ import annotations

from typing import Any, Protocol

from arcengine import FrameData

Grid = list[list[int]]

HUD_COLOUR = 6

# Objects larger than this are scenery and are left alone; small ones animate.
MAX_SPRITE_CELLS = 4


class Environment(Protocol):
    """The surface this wraps: anything that returns FrameData."""

    def reset(self) -> FrameData: ...

    def step(self, action: Any) -> FrameData: ...


class NoiseWrapper:
    """Wraps an environment so its frames carry measured board noise."""

    def __init__(
        self,
        environment: Environment,
        *,
        hud: bool = True,
        animate: bool = True,
        sprite_colour: int | None = None,
        hud_colour: int = HUD_COLOUR,
        max_sprite_cells: int = MAX_SPRITE_CELLS,
    ) -> None:
        """`sprite_colour` restricts the animation to one colour; None animates all small ones.

        Animating every small object rather than one guessed colour matters: an
        earlier version picked the rarest colour, which on our own walking game
        selected the goal instead of the player and left control learning
        untouched — the wrapper then failed to reproduce the failure it exists
        to reproduce.
        """
        self._environment = environment
        self._hud = hud
        self._animate = animate
        self._sprite_colour = sprite_colour
        self._hud_colour = hud_colour
        self._max_sprite_cells = max_sprite_cells
        self._ticks = 0

    def __getattr__(self, name: str) -> Any:
        """Pass anything else — actions_used, optimal_actions — straight through."""
        return getattr(self._environment, name)

    def reset(self) -> FrameData:
        self._ticks = 0
        return self._noisy(self._environment.reset())

    def step(self, action: Any) -> FrameData:
        # Advance before the action resolves, so a refused action ticks the HUD
        # too and it cannot be identified by whether the board responded.
        self._ticks += 1
        return self._noisy(self._environment.step(action))

    # --- rendering ----------------------------------------------------------

    def _noisy(self, frame: FrameData) -> FrameData:
        stack = frame.frame or []
        if not stack:
            return frame
        board = [row[:] for row in stack[-1]]

        if self._animate:
            self._blur(board)
        if self._hud:
            board.append(self._bar(len(board[0])))

        return frame.model_copy(update={"frame": [*stack[:-1], board]})

    def _blur(self, board: Grid) -> None:
        """Light one empty cell beside each small object, on alternate ticks."""
        if self._ticks % 2 == 0:
            return
        for colour in self._animating_colours(board):
            self._blur_one(board, colour)

    def _animating_colours(self, board: Grid) -> list[int]:
        if self._sprite_colour is not None:
            return [self._sprite_colour]
        counts: dict[int, int] = {}
        for row in board:
            for value in row:
                counts[value] = counts.get(value, 0) + 1
        return sorted(
            colour for colour, n in counts.items() if colour != 0 and n <= self._max_sprite_cells
        )

    def _blur_one(self, board: Grid, colour: int) -> None:
        for r, row in enumerate(board):
            for c, value in enumerate(row):
                if value != colour:
                    continue
                for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nr, nc = r + dr, c + dc
                    inside = 0 <= nr < len(board) and 0 <= nc < len(board[0])
                    if inside and board[nr][nc] == 0:
                        board[nr][nc] = colour
                        return
                return

    def _bar(self, width: int) -> list[int]:
        filled = max(0, width - (self._ticks % (width + 1)))
        return [self._hud_colour] * filled + [0] * (width - filled)
