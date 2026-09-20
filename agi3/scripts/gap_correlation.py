"""Put a number on how badly simulation predicts real performance.

This project has shown four times that a method convincing in one arena fails
in the next, but always as pass-or-fail anecdotes. A single correlation is more
useful: if tuning against a simulator improved real performance, configurations
that score better there would score better here too.

So the same knobs are swept twice. Each configuration of the control learner is
scored on the noise-calibrated mock, by how far a policy built on it actually
gets, and on recorded real boards, by how often the mapping it recovers matches
the label. The rank correlation between those two columns is the number: near
+1 means the simulator is a usable proxy, near 0 means it tells you nothing,
and negative means tuning against it makes real performance worse.
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from arcengine import GameAction

from arcagi3.budget import run_episode
from arcagi3.control import ControlLearner
from arcagi3.navigator import NavigatorAgent
from arcagi3.noisy_mock import NoisyEnvironment
from arcagi3.replay import LABEL_DIRECTION, read_transitions

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
BY_NAME: dict[str, GameAction] = {action.name: action for action in GameAction}

ESTIMATORS = ("centroid", "overlap")
MIN_OBSERVATIONS = (2, 3, 5)
SPRITE_SHARES = (0.05, 0.10, 0.20)


@dataclass(frozen=True)
class Config:
    estimator: str
    min_observations: int
    max_sprite_share: float

    def build(self) -> ControlLearner:
        return ControlLearner(
            estimator=self.estimator,
            min_observations=self.min_observations,
            max_sprite_share=self.max_sprite_share,
        )

    def __str__(self) -> str:
        return f"{self.estimator[:4]}/obs={self.min_observations}/share={self.max_sprite_share}"


def score_on_mock(config: Config, cap: int) -> float:
    """Levels a policy using this configuration clears on the noisy mock."""
    import arcagi3.navigator as navigator_module

    original = navigator_module.ControlLearner
    navigator_module.ControlLearner = config.build
    try:
        agent = NavigatorAgent()
        agent.control = config.build()
        result = run_episode(agent, NoisyEnvironment(), max_actions=cap)
    finally:
        navigator_module.ControlLearner = original
    return result.levels_completed


def score_on_traces(config: Config, files: list[str]) -> float:
    """Share of recovered mappings that match the recorded label."""
    learned = correct = 0
    for path in files:
        learner, truth = config.build(), {}
        for transition in read_transitions(path):
            if not transition.is_movement_label or not transition.board_changed:
                continue
            action = BY_NAME.get(transition.action_name)
            if action is None:
                continue
            truth[action] = LABEL_DIRECTION[transition.action_display]
            learner.observe(transition.before, transition.after, action)
        mapping = learner.mapping()
        learned += len(mapping)
        correct += sum(1 for a, d in mapping.items() if truth.get(a) == d)
    return correct / learned if learned else 0.0


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, ties averaged. Implemented here to avoid a dependency."""

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda i: values[i])
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            shared = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = shared
            i = j + 1
        return out

    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
    vx = sum((a - mx) ** 2 for a in rx) ** 0.5
    vy = sum((b - my) ** 2 for b in ry) ** 0.5
    return cov / (vx * vy) if vx and vy else 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Correlate mock score with real accuracy")
    parser.add_argument("--traces", default=DEFAULT_TRACES)
    parser.add_argument("--games", type=int, default=12, help="how many games to score against")
    parser.add_argument("--max-actions", type=int, default=400)
    parser.add_argument("--json", dest="json_out")
    args = parser.parse_args(argv)

    files = sorted(glob.glob(f"{args.traces}/*_p0_events.jsonl"))[: args.games]
    if not files:
        print(f"no traces in {args.traces}", file=sys.stderr)
        return 2

    configs = [
        Config(estimator, observations, share)
        for estimator, observations, share in itertools.product(
            ESTIMATORS, MIN_OBSERVATIONS, SPRITE_SHARES
        )
    ]

    print(f"{'configuration':<30} {'mock levels':>12} {'real accuracy':>14}")
    print("-" * 58)
    rows = []
    for index, config in enumerate(configs, start=1):
        print(f"  [{index}/{len(configs)}] {config}", file=sys.stderr, flush=True)
        mock = score_on_mock(config, args.max_actions)
        real = score_on_traces(config, files)
        rows.append((str(config), mock, real))
        print(f"{str(config):<30} {mock:>12.0f} {real:>13.0%}")

    print("-" * 58)
    rho = spearman([m for _, m, _ in rows], [r for _, _, r in rows])
    print(f"\nrank correlation between the two columns: {rho:+.2f}")
    print(f"(games scored against: {len(files)}; configurations: {len(rows)})")

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"rows": rows, "spearman": rho, "games": len(files)}, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
