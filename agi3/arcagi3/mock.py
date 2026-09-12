"""An offline stand-in for an ARC-AGI-3 environment.

The competition SDK talks to a remote server and spends scorecard quota on every
interaction, which makes it a poor place to iterate on a policy. This module
speaks the same types the real wrapper returns — `FrameData`, `GameAction`,
`GameState` straight out of `arcengine` — against a deterministic toy game, so
policy code written here runs unchanged against the real thing.

The game is a cursor-to-target walk. It is not meant to be interesting; it is
meant to have a *known optimal action count* per level, so efficiency can be
measured rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

from arcagi3.actions import INTERACT, MOVES

EMPTY = 0
TARGET = 2
CURSOR = 4
WALL = 8


@dataclass(frozen=True)
class Level:
    """One level: a walled grid, a start and a target."""

    height: int
    width: int
    start: tuple[int, int]
    target: tuple[int, int]
    walls: frozenset[tuple[int, int]] = field(default_factory=frozenset)

    @property
    def optimal_actions(self) -> int:
        """Fewest actions that can finish this level: the walk, plus one interact.

        Valid only while no wall blocks the L-shaped path, which holds for the
        levels defined below. It is the baseline efficiency is measured against.
        """
        dy = abs(self.target[0] - self.start[0])
        dx = abs(self.target[1] - self.start[1])
        return dy + dx + 1


LEVELS: tuple[Level, ...] = (
    Level(height=6, width=6, start=(0, 0), target=(0, 3)),
    Level(height=8, width=8, start=(7, 0), target=(2, 5)),
    Level(
        height=8,
        width=8,
        start=(0, 0),
        target=(7, 7),
        walls=frozenset({(3, 1), (3, 2), (3, 3), (5, 5), (5, 6)}),
    ),
)


class MockEnvironment:
    """A local environment exposing the same surface an agent sees in competition."""

    game_id = "mock-cursor-walk"

    def __init__(self, levels: tuple[Level, ...] = LEVELS) -> None:
        if not levels:
            raise ValueError("need at least one level")
        self._levels = levels
        self._level_index = 0
        self._pos = levels[0].start
        self._state = GameState.NOT_PLAYED
        self._actions_used = 0
        self._levels_completed = 0

    # --- introspection used by tests and by budget accounting ---------------

    @property
    def actions_used(self) -> int:
        return self._actions_used

    @property
    def optimal_actions(self) -> int:
        """Baseline action count for a perfect run of every level."""
        return sum(level.optimal_actions for level in self._levels)

    @property
    def level(self) -> Level:
        return self._levels[self._level_index]

    # --- the agent-facing surface ------------------------------------------

    def reset(self) -> FrameData:
        self._level_index = 0
        self._pos = self._levels[0].start
        self._state = GameState.NOT_FINISHED
        self._levels_completed = 0
        return self._frame(GameAction.RESET, full_reset=True)

    def step(self, action: GameAction) -> FrameData:
        """Apply one action. Illegal actions cost a turn and change nothing.

        Charging for an illegal action is deliberate: the real scorecard counts
        every action taken, so a policy that ignores `available_actions` should
        be punished here too rather than getting a free retry.
        """
        if self._state in (GameState.WIN, GameState.GAME_OVER):
            return self._frame(action)

        self._actions_used += 1

        if action is GameAction.RESET:
            self._pos = self.level.start
            return self._frame(action, full_reset=True)

        if action in MOVES and action in self.available_actions():
            dy, dx = MOVES[action]
            self._pos = (self._pos[0] + dy, self._pos[1] + dx)
        elif action is INTERACT and self._pos == self.level.target:
            self._advance_level()

        return self._frame(action)

    def available_actions(self) -> list[GameAction]:
        """Actions that would do something from the current position.

        The real API ships this per frame and it changes as the game goes on, so
        a policy must read it each step rather than assume all seven are legal.
        """
        if self._state in (GameState.WIN, GameState.GAME_OVER):
            return []

        level, (y, x) = self.level, self._pos
        actions = [GameAction.RESET]
        for action, (dy, dx) in MOVES.items():
            ny, nx = y + dy, x + dx
            in_bounds = 0 <= ny < level.height and 0 <= nx < level.width
            if in_bounds and (ny, nx) not in level.walls:
                actions.append(action)
        if (y, x) == level.target:
            actions.append(INTERACT)
        return actions

    # --- internals ----------------------------------------------------------

    def _advance_level(self) -> None:
        self._levels_completed += 1
        if self._level_index + 1 < len(self._levels):
            self._level_index += 1
            self._pos = self.level.start
        else:
            self._state = GameState.WIN

    def _grid(self) -> list[list[int]]:
        level = self.level
        grid = [[EMPTY] * level.width for _ in range(level.height)]
        for wy, wx in level.walls:
            grid[wy][wx] = WALL
        ty, tx = level.target
        grid[ty][tx] = TARGET
        cy, cx = self._pos
        grid[cy][cx] = CURSOR
        return grid

    def _frame(self, action: GameAction, *, full_reset: bool = False) -> FrameData:
        return FrameData(
            game_id=self.game_id,
            # The real API returns a stack of grids, not a single board.
            frame=[self._grid()],
            state=self._state,
            levels_completed=self._levels_completed,
            win_levels=len(self._levels),
            action_input=ActionInput(id=action, data={}),
            guid=None,
            full_reset=full_reset,
            available_actions=[a.value for a in self.available_actions()],
        )
