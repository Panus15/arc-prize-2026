"""Failure four, reproduced: three ways to read a move, judged in two places.

For each estimator the control learner can use — centroid, overlap (align the
colour's cells between frames), fallback (overlap, else centroid) — this reports

  noisy mock   levels the frozen walker (navigator_v1) clears in the
               noise-calibrated mock with that estimator, 400 actions
  real boards  how often the learned action-to-direction mapping matches the
               recorded labels, pass 0 of each of the 25 public games, and in
               how many games any mapping was learned at all

The frozen walker rebuilds its learner when predictions fail; it is made to
rebuild with the same estimator, or the comparison would quietly revert to
centroid mid-game.

    python scripts/estimator_comparison.py
"""

from __future__ import annotations

import argparse
import glob
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arcengine import GameAction  # noqa: E402

import arcagi3.navigator_v1 as frozen  # noqa: E402
from arcagi3.budget import run_episode  # noqa: E402
from arcagi3.control import ControlLearner  # noqa: E402
from arcagi3.noisy_mock import NoisyEnvironment  # noqa: E402
from arcagi3.replay import LABEL_DIRECTION, read_transitions  # noqa: E402

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
ESTIMATORS = ("centroid", "overlap", "fallback")
BY_NAME = {action.name: action for action in GameAction}


def mock_levels(estimator: str) -> int:
    original = frozen.ControlLearner
    frozen.ControlLearner = partial(ControlLearner, estimator=estimator)
    try:
        return run_episode(frozen.NavigatorAgent(), NoisyEnvironment(), max_actions=400).levels_completed
    finally:
        frozen.ControlLearner = original


def real_accuracy(estimator: str, files: list[str]) -> tuple[int, int, int]:
    """(correct, learned, games with any mapping) over the recorded boards."""
    correct = learned = fired = 0
    for path in files:
        learner, truth = ControlLearner(estimator=estimator), {}
        for t in read_transitions(path):
            if not t.is_movement_label or not t.board_changed:
                continue
            action = BY_NAME.get(t.action_name)
            if action is None:
                continue
            truth[action] = LABEL_DIRECTION[t.action_display]
            learner.observe(t.before, t.after, action)
        mapping = learner.mapping()
        if mapping:
            fired += 1
            learned += len(mapping)
            correct += sum(1 for a, d in mapping.items() if truth.get(a) == d)
    return correct, learned, fired


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", default=DEFAULT_TRACES)
    args = parser.parse_args(argv)
    files = sorted(glob.glob(f"{args.traces}/*_p0_events.jsonl"))
    if not files:
        print(f"no recorded runs under {args.traces}")
        return 2

    print(f"{'estimator':<10}{'noisy mock':>12}{'real boards':>14}{'games':>9}")
    for estimator in ESTIMATORS:
        levels = mock_levels(estimator)
        correct, learned, fired = real_accuracy(estimator, files)
        print(f"{estimator:<10}{levels:>9}/3{correct / learned:>14.0%}{fired:>6}/{len(files)}"
              f"   ({correct}/{learned} mappings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
