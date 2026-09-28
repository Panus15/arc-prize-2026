"""Failure one, reproduced: matching objects between frames by exact shape.

The first control learner required a move to show exactly one object moving and
nothing else changing (`effects.diff(...).sole_movement()`), matching objects
between frames by a position-invariant shape hash. This measures how often that
condition holds on movement transitions:

  - in our quiet mock and our noise-calibrated mock, under a seeded random walk;
  - on the recorded real runs, pass 0 of each of the 25 public games, over the
    transitions whose recorded label is a direction.

It also counts what the diff saw on the real transitions — objects appearing,
moving, vanishing — which is the mechanism: an animating sprite does not match
itself between frames, so it reads as one object vanishing and another appearing.

    python scripts/object_matching.py
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arcengine import GameAction  # noqa: E402

from arcagi3.effects import diff  # noqa: E402
from arcagi3.mock import MockEnvironment  # noqa: E402
from arcagi3.noisy_mock import NoisyEnvironment  # noqa: E402
from arcagi3.perception import segment  # noqa: E402
from arcagi3.replay import LABEL_DIRECTION, read_transitions  # noqa: E402

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
MOVES = (GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4)


def mock_rate(make, steps: int, seed: int = 0) -> tuple[int, int]:
    """(movement transitions, those with a sole movement) under a random walk."""
    rng = random.Random(seed)
    env = make()
    frame = env.reset()
    moves = sole = 0
    for _ in range(steps):
        legal = [a for a in MOVES if a.value in frame.available_actions]
        if not legal:
            frame = env.reset()
            continue
        before = frame.frame[-1]
        frame = env.step(rng.choice(legal))
        after = frame.frame[-1]
        if before == after:
            continue  # refused: not a movement transition
        moves += 1
        sole += diff(segment(before), segment(after)).sole_movement() is not None
    return moves, sole


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path(DEFAULT_TRACES))
    parser.add_argument("--mock-steps", type=int, default=500)
    args = parser.parse_args(argv)

    print("movement transitions showing exactly one object moving and nothing else\n")
    for name, make in (("quiet mock", MockEnvironment), ("noise-calibrated mock", NoisyEnvironment)):
        moves, sole = mock_rate(make, args.mock_steps)
        print(f"  {name:<24} {sole:>5} of {moves:>5}  = {sole / moves:.1%}")

    paths = sorted(args.traces.glob("*_p0_events.jsonl"))
    if not paths:
        print(f"\nno recorded runs under {args.traces}")
        return 2
    kinds: Counter[str] = Counter()
    moves = sole = 0
    recovered: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        game = path.name.split("-")[0]
        for t in read_transitions(path):
            if t.action_display not in LABEL_DIRECTION:
                continue
            moves += 1
            d = diff(segment(t.before), segment(t.after))
            kinds.update(change.kind for change in d.changes)
            if d.sole_movement() is not None:
                sole += 1
                recovered[game].add(t.action_display)
    full = sum(1 for dirs in recovered.values() if len(dirs) == 4)
    print(f"  {'recorded real runs':<24} {sole:>5} of {moves:>5}  = {sole / moves:.1%}"
          f"   ({len(paths)} games, pass 0)")
    print(f"\ngames where all four directions were recovered: {full} of {len(paths)}")
    print("what the diff saw on the real movement transitions: "
          + ", ".join(f"{kind} {kinds[kind]:,}" for kind in ("appeared", "moved", "vanished")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
