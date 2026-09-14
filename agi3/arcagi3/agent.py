"""Agent base and reference policies.

ARC-AGI-3 scores efficiency, not just completion: actions are counted against a
per-level baseline while the reasoning behind them costs nothing. So the base
class here makes two things structural rather than optional — a policy may only
return an action the current frame says is available, and every action it takes
is counted.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

from arcengine import FrameData, GameAction, GameState

from arcagi3.actions import INTERACT, MOVES, actions_from_values
from arcagi3.mock import CURSOR, TARGET


class IllegalActionError(RuntimeError):
    """A policy returned an action the frame did not offer."""


class BaseAgent(ABC):
    """Chooses actions from frames. Subclasses implement `choose_action`."""

    name: str = "base"

    @abstractmethod
    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        """Pick the next action. Must be one of `latest.available_actions`."""

    def is_done(self, frames: list[FrameData], latest: FrameData) -> bool:
        return latest.state in (GameState.WIN, GameState.GAME_OVER)

    def act(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        """`choose_action` with the legality check applied.

        Checking here rather than trusting the policy means a bug surfaces as a
        loud failure during development instead of as silently wasted actions in
        a scored run, where every wasted action costs efficiency.
        """
        action = self.choose_action(frames, latest)
        if action.value not in latest.available_actions:
            raise IllegalActionError(
                f"{self.name} chose {action.name}, but this frame offers "
                f"{[a.name for a in actions_from_values(latest.available_actions)]}"
            )
        return action


class RandomAgent(BaseAgent):
    """Uniform choice over the legal actions — the floor to beat.

    RESET is excluded unless it is the only option: it is always legal and never
    progresses, so including it makes the floor artificially bad.
    """

    name = "random"

    def __init__(self, seed: int | None = 0) -> None:
        self._rng = random.Random(seed)

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        actions = actions_from_values(latest.available_actions)
        useful = [a for a in actions if a is not GameAction.RESET]
        return self._rng.choice(useful or actions)


class GreedyAgent(BaseAgent):
    """Walks the cursor toward the target, reading both from the frame.

    This is not a general solver — it reads the mock's colour convention. It
    exists to prove the environment is solvable at the optimal action count, so
    that the efficiency numbers a real policy produces have a known ceiling.
    """

    name = "greedy"

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        grid = latest.frame[0]
        cursor = _find(grid, CURSOR)
        target = _find(grid, TARGET)
        available = set(actions_from_values(latest.available_actions))

        if cursor is None or target is None or cursor == target:
            if INTERACT in available:
                return INTERACT
            return _fallback(available)

        dy = target[0] - cursor[0]
        dx = target[1] - cursor[1]
        # Close the larger gap first; it keeps the walk inside the L-shaped path
        # the baseline assumes.
        preferred = []
        if abs(dy) >= abs(dx):
            preferred = [_step(dy, 0), _step(0, dx)]
        else:
            preferred = [_step(0, dx), _step(dy, 0)]

        for action in preferred:
            if action is not None and action in available:
                return action
        return _fallback(available)


def _fallback(available: set[GameAction]) -> GameAction:
    """Lowest-numbered action that is not RESET, or RESET if there is none.

    Iterating the set directly would be non-deterministic: GameAction members
    hash by identity, so set order changes between processes and the same board
    would produce different play on different runs. Anything a competition run
    reports has to be reproducible, so the tie is broken by action value.
    """
    usable = sorted(available - {GameAction.RESET}, key=lambda a: a.value)
    return usable[0] if usable else GameAction.RESET


def _find(grid: list[list[int]], symbol: int) -> tuple[int, int] | None:
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            if value == symbol:
                return y, x
    return None


def _step(dy: int, dx: int) -> GameAction | None:
    if dy == 0 and dx == 0:
        return None
    unit = (0 if dy == 0 else (1 if dy > 0 else -1), 0 if dx == 0 else (1 if dx > 0 else -1))
    for action, delta in MOVES.items():
        if delta == unit:
            return action
    return None
