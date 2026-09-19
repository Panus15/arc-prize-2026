"""Working out which object the buttons move, on boards that will not hold still.

`effects.diff` can say "one object moved two left", which is enough to learn the
controls on a tidy board. Real ARC-AGI-3 boards are not tidy: measured over 2,276
recorded movement transitions from 25 official games, exactly 10 of them — 0.4% —
produced a single unambiguous object movement. Sprites change shape between
frames, HUD bars tick, and things appear and vanish, so matching objects by an
exact shape hash loses the player almost every time.

What survives that noise is coarser: the centre of mass of each colour. A sprite
that animates while moving still shifts its colour's centroid in the direction it
went, and a HUD bar that ticks every step shifts the same way no matter which
button was pressed — so requiring the shift to *depend on the action* separates
the two. On the same recordings this recovers 79% of action-to-direction
mappings, and gets every mapping right in 11 of 17 games where the method fires.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Collection
from dataclasses import dataclass, field

from arcengine import GameAction

from arcagi3.actions import describe

Grid = list[list[int]]
Delta = tuple[int, int]

# A colour covering more than this share of the board is scenery, not a sprite.
# Measured: the player's colour never came close to this on the recorded games.
MAX_SPRITE_SHARE = 0.10

# Centroid shifts smaller than this are noise from a sprite changing shape in
# place rather than evidence of movement.
MOVEMENT_EPSILON = 0.05

# Below this many observations an action's dominant direction is not yet worth
# believing; three was enough to separate signal from noise on the recordings.
MIN_OBSERVATIONS = 3


# How far a sprite is assumed to travel in one action. Two covers a normal step
# and a little overshoot without making the search expensive.
MAX_STEP = 2


def colour_cells(grid: Grid) -> dict[int, set[tuple[int, int]]]:
    """Every cell of every colour, in one pass."""
    cells: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            cells[value].add((r, c))
    return cells


def overlap_displacement(
    before: set[tuple[int, int]],
    after: set[tuple[int, int]],
    max_step: int = MAX_STEP,
) -> Delta | None:
    """The shift that best lines a colour's cells up between two frames.

    A centroid is the obvious way to measure this and it is fragile: a sprite
    that animates asymmetrically gains a cell on one side, which drags the mean
    sideways and turns a straight move into a diagonal one. Aligning the cells
    themselves does not care about the extra cell, only about where the body of
    the shape went.

    Ties prefer a real move over standing still, because an action was taken and
    "nothing moved" should have to be the only explanation rather than merely a
    tied one — that single rule is what makes this exact rather than
    approximate on an animating sprite.
    """
    if not before or not after:
        return None

    scored: list[tuple[int, Delta]] = []
    for dr in range(-max_step, max_step + 1):
        for dc in range(-max_step, max_step + 1):
            shifted = {(r + dr, c + dc) for r, c in before}
            scored.append((len(shifted & after), (dr, dc)))

    best = max(count for count, _ in scored)
    if best == 0:
        return None  # nothing lines up; the shape did not merely move
    tied = [delta for count, delta in scored if count == best]
    moves = [delta for delta in tied if delta != (0, 0)]
    pool = moves or tied
    return min(pool, key=lambda d: (abs(d[0]) + abs(d[1]), d))


def colour_centroids(grid: Grid) -> dict[int, tuple[float, float, int]]:
    """Centre of mass and cell count for every colour present."""
    totals: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            entry = totals[value]
            entry[0] += r
            entry[1] += c
            entry[2] += 1
    return {v: (t[0] / t[2], t[1] / t[2], int(t[2])) for v, t in totals.items()}


def direction_of(shift: tuple[float, float], epsilon: float = MOVEMENT_EPSILON) -> Delta:
    """Reduce a centroid shift to one of the nine grid directions."""
    dr, dc = shift
    return (
        (dr > epsilon) - (dr < -epsilon),
        (dc > epsilon) - (dc < -epsilon),
    )


@dataclass
class ControlLearner:
    """Accumulates evidence about which colour moves, and which way, per action."""

    max_sprite_share: float = MAX_SPRITE_SHARE
    min_observations: int = MIN_OBSERVATIONS
    #: "centroid" tracks the colour's centre of mass; "overlap" aligns its cells.
    #:
    #: The default is centroid because recorded real boards say so, not because
    #: it is the better idea. On our noise-calibrated mock overlap is decisively
    #: better — it recovers the controls exactly where the centroid reports
    #: diagonals, and the policy goes from clearing no levels to clearing all of
    #: them. On real frames it is decisively worse: 55% against the centroid's
    #: 79%. The two arenas disagree, and real data outranks a mock we wrote.
    #: See docs/estimator-comparison.md.
    estimator: str = "centroid"
    # colour -> action -> direction -> count
    _votes: dict[int, dict[GameAction, Counter]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(Counter))
    )
    _samples: int = 0

    @property
    def samples(self) -> int:
        return self._samples

    def observe(self, before: Grid, after: Grid, action: GameAction) -> None:
        """Record how every plausible sprite colour shifted under `action`."""
        if not before or not after:
            return
        cells = len(before) * len(before[0])
        limit = cells * self.max_sprite_share
        self._samples += 1

        if self.estimator == "centroid":
            start = colour_centroids(before)
            end = colour_centroids(after)
            for colour in start.keys() & end.keys():
                if start[colour][2] > limit:
                    continue  # scenery
                shift = (end[colour][0] - start[colour][0], end[colour][1] - start[colour][1])
                self._votes[colour][action][direction_of(shift)] += 1
            return

        start_cells = colour_cells(before)
        end_cells = colour_cells(after)
        for colour in start_cells.keys() & end_cells.keys():
            if len(start_cells[colour]) > limit:
                continue  # scenery
            delta = overlap_displacement(start_cells[colour], end_cells[colour])
            if delta is not None:
                self._votes[colour][action][direction_of(delta)] += 1

    def candidate(self) -> tuple[int, dict[GameAction, Delta], float] | None:
        """The colour that best behaves like the thing under our control.

        Scored by how many distinct directions it can be pushed in, then by how
        consistently each action produces the same one. A colour that always
        drifts the same way regardless of the button — a timer bar — offers one
        direction and loses to a real sprite.
        """
        best: tuple[int, dict[GameAction, Delta], float] | None = None
        for colour, per_action in self._votes.items():
            mapping: dict[GameAction, Delta] = {}
            agreement = 0.0
            for action, counts in per_action.items():
                total = sum(counts.values())
                if total < self.min_observations:
                    continue
                dominant, hits = counts.most_common(1)[0]
                if dominant == (0, 0):
                    continue  # this action does not move this colour
                mapping[action] = dominant
                agreement += hits / total
            if len(mapping) < 2:
                continue
            score = agreement / len(mapping)
            distinct = len({d for d in mapping.values()})
            if best is None or (distinct, score) > (len(set(best[1].values())), best[2]):
                best = (colour, mapping, score)
        return best

    def mapping(self) -> dict[GameAction, Delta]:
        """Best current guess at what each action does."""
        found = self.candidate()
        return dict(found[1]) if found else {}

    def controlled_colour(self) -> int | None:
        found = self.candidate()
        return found[0] if found else None

    def confidence(self) -> float:
        """How consistently the winning colour obeys the mapping, 0 to 1."""
        found = self.candidate()
        return found[2] if found else 0.0

    def action_for(self, direction: Delta) -> GameAction | None:
        """Which action pushes the controlled colour exactly `direction`, if any."""
        for action, delta in self.mapping().items():
            if delta == direction:
                return action
        return None

    def best_action_for(
        self, direction: Delta, allowed: Collection[GameAction] | None = None
    ) -> GameAction | None:
        """The action that moves furthest along `direction`, exact or not.

        Insisting on an exact match fails as soon as an effect is not a clean
        cardinal step, and on a real board it often is not: a sprite that
        animates asymmetrically drags its colour's centroid sideways as it
        moves, so pressing down is learned as down-and-right. Scoring by how
        much of the wanted direction an action actually delivers keeps such a
        mapping usable, and reduces to the exact match when the effects are
        clean. Ties break by action value so play stays reproducible.
        """
        best: tuple[int, int, GameAction] | None = None
        for action, delta in self.mapping().items():
            if allowed is not None and action not in allowed:
                continue
            progress = delta[0] * direction[0] + delta[1] * direction[1]
            if progress <= 0:
                continue  # sideways or backwards is not progress
            drift = abs(delta[0] * direction[1] - delta[1] * direction[0])
            # Most progress first, then least sideways drift, then lowest value.
            candidate = (-progress, drift, action.value)
            if best is None or candidate < (-best[0], best[1], best[2].value):
                best = (progress, drift, action)
        return best[2] if best else None

    def summary(self) -> str:
        found = self.candidate()
        if not found:
            return f"(no control found after {self._samples} samples)"
        colour, mapping, score = found
        moves = ", ".join(
            f"{describe(a)}={d[0]:+d},{d[1]:+d}"
            for a, d in sorted(mapping.items(), key=lambda kv: kv[0].value)
        )
        return f"colour {colour} @ {score:.0%} confidence over {self._samples} samples: {moves}"
