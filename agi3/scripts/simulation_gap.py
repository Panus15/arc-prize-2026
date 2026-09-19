"""Measure the gap between doing well in simulation and doing well for real.

Three times on this benchmark a method has looked sound against an environment
we wrote and then failed against measured reality. That pattern, not any one
policy, is the thing worth reporting — so this produces the table it rests on
with a single command.

Two arenas are played and compared directly, because they ask the same question
of the same policies: the quiet mock we started with, and a mock calibrated to
noise measured from recorded games. A third column is not a game at all but a
component check against recorded boards, and is kept separate for that reason —
a mapping being right is not the same as a policy being able to play.
"""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from arcengine import GameAction

from arcagi3.agent import BaseAgent, GreedyAgent, RandomAgent
from arcagi3.budget import run_episode
from arcagi3.control import ControlLearner
from arcagi3.explorer import ExplorerAgent
from arcagi3.mock import MockEnvironment
from arcagi3.navigator import NavigatorAgent
from arcagi3.noisy_mock import NoisyEnvironment
from arcagi3.replay import LABEL_DIRECTION, game_id, read_transitions

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)

BY_NAME: dict[str, GameAction] = {action.name: action for action in GameAction}

POLICIES: dict[str, Callable[[], BaseAgent]] = {
    "random": lambda: RandomAgent(seed=0),
    "greedy": GreedyAgent,
    "explorer": ExplorerAgent,
    "navigator": NavigatorAgent,
}


@dataclass(frozen=True)
class Played:
    """How a policy fared in one arena."""

    levels: int
    total: int
    actions: int
    won: bool

    def __str__(self) -> str:
        return f"{'WIN' if self.won else 'lost'} {self.levels}/{self.total} in {self.actions}"


def play(policy: Callable[[], BaseAgent], arena: Callable[[], object], cap: int) -> Played:
    result = run_episode(policy(), arena(), max_actions=cap)  # type: ignore[arg-type]
    return Played(
        levels=result.levels_completed,
        total=result.total_levels,
        actions=result.actions_used,
        won=result.won,
    )


def control_accuracy_on_traces(directory: str, limit: int) -> dict[str, float | int] | None:
    """How often the learned mapping matches the label, on recorded boards.

    This is a component check, not a game: it asks whether the controls can be
    recovered from real frames, which the playing columns show is necessary but
    nowhere near sufficient.
    """
    files = sorted(glob.glob(f"{directory}/*_p0_events.jsonl"))[:limit]
    if not files:
        return None

    learned = correct = fired = 0
    for index, path in enumerate(files, start=1):
        print(f"  [{index}/{len(files)}] {game_id(path)}", file=sys.stderr, flush=True)
        learner, truth = ControlLearner(), {}
        for transition in read_transitions(path):
            if not transition.is_movement_label or not transition.board_changed:
                continue
            action = BY_NAME.get(transition.action_name)
            if action is None:
                continue
            truth[action] = LABEL_DIRECTION[transition.action_display]
            learner.observe(transition.before, transition.after, action)
        mapping = learner.mapping()
        if not mapping:
            continue
        fired += 1
        learned += len(mapping)
        correct += sum(1 for a, d in mapping.items() if truth.get(a) == d)

    return {
        "games": len(files),
        "games_with_a_mapping": fired,
        "mappings": learned,
        "correct": correct,
        "accuracy": correct / learned if learned else 0.0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the simulation-to-reality gap")
    parser.add_argument("--max-actions", type=int, default=400)
    parser.add_argument("--traces", default=DEFAULT_TRACES)
    parser.add_argument("--trace-limit", type=int, default=25)
    parser.add_argument("--skip-traces", action="store_true")
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args(argv)

    arenas: dict[str, Callable[[], object]] = {
        "quiet mock": MockEnvironment,
        "noise-calibrated mock": NoisyEnvironment,
    }

    print(f"{'policy':<11} {'learns?':>8} " + " ".join(f"{name:>24}" for name in arenas))
    print("-" * (21 + 25 * len(arenas)))

    table: dict[str, dict[str, str]] = {}
    for name, factory in POLICIES.items():
        learns = "no" if name in ("random", "greedy") else "yes"
        cells = {arena: play(factory, make, args.max_actions) for arena, make in arenas.items()}
        table[name] = {arena: str(result) for arena, result in cells.items()}
        rendered = " ".join(f"{str(cells[arena]):>24}" for arena in arenas)
        print(f"{name:<11} {learns:>8} {rendered}")

    component: dict[str, float | int] | None = None
    if not args.skip_traces:
        print("\ncomponent check on recorded boards:", file=sys.stderr)
        component = control_accuracy_on_traces(args.traces, args.trace_limit)
        if component is None:
            print("\n(no traces found; component check skipped)")
        else:
            print(
                f"\ncontrol mapping recovered from real frames: "
                f"{component['correct']}/{component['mappings']} correct "
                f"({component['accuracy']:.0%}) across "
                f"{component['games_with_a_mapping']}/{component['games']} games"
            )

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"arenas": table, "component": component}, indent=2), encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
