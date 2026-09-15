"""Measure how much evidence the control learner needs, on recorded real games.

Everything the policy does rests on working out what the buttons do. On our own
offline environment that looks easy; on real boards it is not, and the question
that actually matters for the competition is quantitative: how many actions must
an agent spend probing before its map is worth acting on, given that every
action counts against the score?

This replays recorded ARC-AGI-3 runs, feeds them to `ControlLearner` in order,
and checks the map it has built at a series of checkpoints against the ground
truth the recordings carry (each action's engine name paired with its human
label). It reports a learning curve, the spread across repeated passes of the
same game, whether the reported confidence is honest, and where the method
fails outright.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from arcengine import GameAction

from arcagi3.control import ControlLearner
from arcagi3.replay import LABEL_DIRECTION, game_id, read_transitions

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)

# Checkpoints in observations fed. Chosen to straddle the region where a policy
# would plausibly stop probing and start acting.
CHECKPOINTS: tuple[int, ...] = (5, 10, 20, 40, 80, 160)

BY_NAME: dict[str, GameAction] = {action.name: action for action in GameAction}


@dataclass
class Snapshot:
    """What the learner believed after a given number of observations."""

    observations: int
    learned: int
    correct: int
    confidence: float


@dataclass
class PassResult:
    """One recorded pass of one game."""

    game: str
    pass_name: str
    movement_transitions: int
    snapshots: list[Snapshot]
    final: Snapshot
    controlled_colour: int | None


def evaluate_pass(path: Path) -> PassResult:
    """Replay one trace, snapshotting the learned map as evidence accumulates."""
    learner = ControlLearner()
    truth: dict[GameAction, tuple[int, int]] = {}
    snapshots: list[Snapshot] = []
    fed = 0
    pending = list(CHECKPOINTS)

    for transition in read_transitions(path):
        if not transition.is_movement_label or not transition.board_changed:
            continue
        action = BY_NAME.get(transition.action_name)
        if action is None:
            continue
        truth[action] = LABEL_DIRECTION[transition.action_display]
        learner.observe(transition.before, transition.after, action)
        fed += 1
        while pending and fed >= pending[0]:
            snapshots.append(_score(learner, truth, pending.pop(0)))

    return PassResult(
        game=game_id(path),
        pass_name=path.name.split("_")[1],
        movement_transitions=fed,
        snapshots=snapshots,
        final=_score(learner, truth, fed),
        controlled_colour=learner.controlled_colour(),
    )


def _score(
    learner: ControlLearner,
    truth: dict[GameAction, tuple[int, int]],
    observations: int,
) -> Snapshot:
    mapping = learner.mapping()
    correct = sum(1 for action, delta in mapping.items() if truth.get(action) == delta)
    return Snapshot(
        observations=observations,
        learned=len(mapping),
        correct=correct,
        confidence=learner.confidence(),
    )


def learning_curve(results: list[PassResult]) -> list[dict[str, float | int]]:
    """Accuracy and coverage at each checkpoint, pooled over every pass."""
    rows: list[dict[str, float | int]] = []
    for checkpoint in CHECKPOINTS:
        learned = correct = fired = eligible = 0
        for result in results:
            if result.movement_transitions < checkpoint:
                continue
            eligible += 1
            snapshot = next((s for s in result.snapshots if s.observations == checkpoint), None)
            if snapshot is None or snapshot.learned == 0:
                continue
            fired += 1
            learned += snapshot.learned
            correct += snapshot.correct
        rows.append(
            {
                "observations": checkpoint,
                "passes_with_enough_data": eligible,
                "passes_producing_a_map": fired,
                "mappings": learned,
                "correct": correct,
                "accuracy": (correct / learned) if learned else 0.0,
            }
        )
    return rows


def calibration(results: list[PassResult], buckets: int = 5) -> list[dict[str, float | int]]:
    """Observed accuracy per reported-confidence band."""
    tallies: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for result in results:
        final = result.final
        if final.learned == 0:
            continue
        index = min(int(final.confidence * buckets), buckets - 1)
        tallies[index][0] += final.correct
        tallies[index][1] += final.learned
    rows = []
    for index in sorted(tallies):
        correct, learned = tallies[index]
        rows.append(
            {
                "confidence_from": index / buckets,
                "confidence_to": (index + 1) / buckets,
                "mappings": learned,
                "correct": correct,
                "accuracy": correct / learned if learned else 0.0,
            }
        )
    return rows


def per_game(results: list[PassResult]) -> list[dict[str, object]]:
    """How each game fared, and how much its passes disagreed."""
    grouped: dict[str, list[PassResult]] = defaultdict(list)
    for result in results:
        grouped[result.game].append(result)

    rows: list[dict[str, object]] = []
    for game, passes in sorted(grouped.items()):
        accuracies = [p.final.correct / p.final.learned for p in passes if p.final.learned]
        fired = len(accuracies)
        colours = Counter(p.controlled_colour for p in passes if p.controlled_colour is not None)
        rows.append(
            {
                "game": game,
                "passes": len(passes),
                "passes_producing_a_map": fired,
                "mean_accuracy": statistics.mean(accuracies) if accuracies else 0.0,
                "accuracy_spread": (
                    max(accuracies) - min(accuracies) if len(accuracies) > 1 else 0.0
                ),
                "mean_movement_transitions": statistics.mean(
                    p.movement_transitions for p in passes
                ),
                "colour_agreement": (
                    colours.most_common(1)[0][1] / fired if fired and colours else 0.0
                ),
            }
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate control learning on recorded runs")
    parser.add_argument("--traces", default=DEFAULT_TRACES, help="directory of *_events.jsonl")
    parser.add_argument("--limit", type=int, help="only the first N trace files")
    parser.add_argument("--json", dest="json_out", help="write the full result here")
    args = parser.parse_args(argv)

    directory = Path(args.traces)
    files = sorted(directory.glob("*_events.jsonl"))
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"no traces found in {directory}", file=sys.stderr)
        return 2

    results: list[PassResult] = []
    for index, path in enumerate(files, start=1):
        print(f"[{index}/{len(files)}] {path.name}", file=sys.stderr, flush=True)
        results.append(evaluate_pass(path))

    curve = learning_curve(results)
    bands = calibration(results)
    games = per_game(results)

    print(f"\ntraces: {len(results)}  games: {len({r.game for r in results})}\n")
    print("-- learning curve --")
    print(f"{'obs':>6} {'passes':>8} {'fired':>7} {'mappings':>9} {'correct':>8} {'accuracy':>9}")
    for row in curve:
        print(
            f"{row['observations']:>6} {row['passes_with_enough_data']:>8} "
            f"{row['passes_producing_a_map']:>7} {row['mappings']:>9} "
            f"{row['correct']:>8} {row['accuracy']:>8.0%}"
        )

    print("\n-- confidence calibration --")
    print(f"{'band':>12} {'mappings':>9} {'correct':>8} {'accuracy':>9}")
    for row in bands:
        band = f"{row['confidence_from']:.1f}-{row['confidence_to']:.1f}"
        print(f"{band:>12} {row['mappings']:>9} {row['correct']:>8} {row['accuracy']:>8.0%}")

    print("\n-- per game --")
    header = f"{'game':<16} {'fired':>7} {'acc':>6} {'spread':>7} {'moves':>7} {'colour':>7}"
    print(header)
    for row in games:
        print(
            f"{row['game']:<16} {row['passes_producing_a_map']:>2}/{row['passes']:<4} "
            f"{row['mean_accuracy']:>5.0%} {row['accuracy_spread']:>6.0%} "
            f"{row['mean_movement_transitions']:>7.0f} {row['colour_agreement']:>6.0%}"
        )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"curve": curve, "calibration": bands, "games": games}, indent=2),
            encoding="utf-8",
        )
        print(f"\nwrote {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
