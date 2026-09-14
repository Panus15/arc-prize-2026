"""Replaying recorded games, so a policy can be checked against real boards.

Everything else here is validated against the offline environment in `mock.py`,
which we wrote — so it can only confirm that the code is consistent with its own
assumptions. Recorded runs from a real ARC-AGI-3 session are the antidote: real
64x64 boards, real action semantics, and a ground-truth label for what each
action was called.

The format read here is the one the Milestone #1 winner's harness writes
(`*_events.jsonl`): one JSON object per line, with `type` in {initial, action,
analysis}. Action records carry the board *after* the action, so a transition is
built by pairing each action record with the board that preceded it.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

Grid = list[list[int]]


@dataclass(frozen=True)
class Transition:
    """One recorded step: the board before, the action, the board after."""

    before: Grid
    after: Grid
    action_name: str
    action_display: str
    level: int
    board_changed: bool
    level_completed: bool
    reward: float

    @property
    def is_movement_label(self) -> bool:
        """True when the recorded label names a direction we can check against."""
        return self.action_display in {"UP", "DOWN", "LEFT", "RIGHT"}


# The direction each label means, as row/column deltas.
LABEL_DIRECTION: dict[str, tuple[int, int]] = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}


def read_transitions(path: str | Path) -> Iterator[Transition]:
    """Yield every action transition in a recorded run, in order.

    Streams the file: a single trace is several megabytes, mostly boards, and
    twenty passes per game across twenty-five games will not fit in memory.
    """
    previous: Grid | None = None
    for line in Path(path).open(encoding="utf-8"):
        if not line.strip():
            continue
        record = json.loads(line)
        kind = record.get("type")
        if kind == "analysis":
            # Model deliberation, no board change; skip without disturbing state.
            continue

        board = record.get("board")
        if board is None:
            continue

        if kind == "action" and previous is not None:
            yield Transition(
                before=previous,
                after=board,
                action_name=str(record.get("action_name") or ""),
                action_display=str(record.get("action_display") or ""),
                level=int(record.get("level") or 0),
                board_changed=bool(record.get("board_changed")),
                level_completed=bool(record.get("level_completed")),
                reward=float(record.get("reward") or 0.0),
            )
        previous = board


def game_id(path: str | Path) -> str:
    """The game a trace belongs to, from its filename."""
    return Path(path).name.split("_")[0]
