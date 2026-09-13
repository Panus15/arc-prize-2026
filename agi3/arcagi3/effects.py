"""What changed between two boards, in terms of objects rather than cells.

A cell-level diff of two 64x64 grids says almost nothing useful: move one
object and hundreds of cells change. Comparing segmentations instead gives the
statement a policy actually needs — "this object moved two left, nothing else
changed" — which is what makes it possible to learn what an action does.

Objects are matched between frames by their position-invariant hash, so the same
shape is recognised wherever it ended up.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from arcagi3.perception import Node, Segmentation

ChangeKind = Literal["moved", "appeared", "vanished", "changed"]
Delta = tuple[int, int]


@dataclass(frozen=True)
class ObjectChange:
    """One object's fate between two frames."""

    kind: ChangeKind
    before: Node | None
    after: Node | None
    delta: Delta | None = None

    def __str__(self) -> str:
        if self.kind == "moved" and self.delta is not None:
            dr, dc = self.delta
            return f"moved {dr:+d},{dc:+d}"
        return self.kind


@dataclass(frozen=True)
class BoardDiff:
    """Every object-level difference between two frames."""

    changes: tuple[ObjectChange, ...]

    @property
    def changed(self) -> bool:
        return bool(self.changes)

    @property
    def moved(self) -> tuple[ObjectChange, ...]:
        return tuple(c for c in self.changes if c.kind == "moved")

    @property
    def appeared(self) -> tuple[ObjectChange, ...]:
        return tuple(c for c in self.changes if c.kind == "appeared")

    @property
    def vanished(self) -> tuple[ObjectChange, ...]:
        return tuple(c for c in self.changes if c.kind == "vanished")

    def sole_movement(self) -> Delta | None:
        """The displacement, when exactly one object moved and nothing else changed.

        This is the clean case that makes an action's meaning unambiguous. When
        several things move at once the action's effect is entangled with game
        dynamics, and attributing it to a single object would be a guess.
        """
        if len(self.changes) != 1:
            return None
        only = self.changes[0]
        return only.delta if only.kind == "moved" else None


def diff(before: Segmentation, after: Segmentation) -> BoardDiff:
    """Object-level difference between two segmentations."""
    changes: list[ObjectChange] = []

    by_hash_before: dict[str, list[Node]] = {}
    for node in before.nodes:
        by_hash_before.setdefault(node.hash, []).append(node)
    by_hash_after: dict[str, list[Node]] = {}
    for node in after.nodes:
        by_hash_after.setdefault(node.hash, []).append(node)

    for shape_hash in sorted(set(by_hash_before) | set(by_hash_after)):
        olds = list(by_hash_before.get(shape_hash, ()))
        news = list(by_hash_after.get(shape_hash, ()))
        changes.extend(_pair_up(olds, news))

    # Objects that merely swapped identity — same count, same hash, same places —
    # produce no entries, so `changed` stays false for a board that did not move.
    return BoardDiff(changes=tuple(changes))


def _pair_up(olds: list[Node], news: list[Node]) -> list[ObjectChange]:
    """Match same-shape objects across frames, nearest first."""
    changes: list[ObjectChange] = []
    remaining = list(news)

    for old in olds:
        if not remaining:
            changes.append(ObjectChange(kind="vanished", before=old, after=None))
            continue
        # Nearest match: an object is far more likely to have shifted a little
        # than to have teleported past another copy of itself.
        best = min(remaining, key=lambda n: _distance(old.top_left, n.top_left))
        remaining.remove(best)
        delta = (
            best.top_left[0] - old.top_left[0],
            best.top_left[1] - old.top_left[1],
        )
        if delta != (0, 0):
            changes.append(ObjectChange(kind="moved", before=old, after=best, delta=delta))

    for leftover in remaining:
        changes.append(ObjectChange(kind="appeared", before=None, after=leftover))
    return changes


def _distance(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
