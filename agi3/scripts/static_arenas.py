"""Walkers played closed-loop in six arenas, including a fixed action list.

The real engine offers the same `available_actions` on every frame. Our first
mock did not, which is how the frozen navigator came to press ACTION5 on sight
(docs/static-actions.md). This plays every walker in every combination of:

    quiet / noisy        noise calibrated from 500 recorded runs, or none
    dynamic / STATIC     the mock's position-dependent offer, or the engine's fixed one
    scrambled            ACTION1-4 remapped, so the controls must be learned

    python scripts/static_arenas.py
    python scripts/static_arenas.py --json-out static-arenas.json
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arcengine import GameAction  # noqa: E402

from arcagi3.agent import RandomAgent  # noqa: E402
from arcagi3.budget import run_episode  # noqa: E402
from arcagi3.mock import MockEnvironment  # noqa: E402
from arcagi3.navigator import NavigatorAgent  # noqa: E402
from arcagi3.navigator_v1 import NavigatorAgent as FrozenNavigator  # noqa: E402
from arcagi3.noisy_mock import NoisyEnvironment  # noqa: E402

SCRAMBLED = {
    GameAction.ACTION1: (0, 1),
    GameAction.ACTION2: (0, -1),
    GameAction.ACTION3: (1, 0),
    GameAction.ACTION4: (-1, 0),
}

ARENAS = {
    "quiet dynamic": lambda: MockEnvironment(),
    "quiet STATIC": lambda: MockEnvironment(static_actions=True),
    "quiet STATIC scrambled": lambda: MockEnvironment(moves=SCRAMBLED, static_actions=True),
    "noisy dynamic": lambda: NoisyEnvironment(),
    "noisy STATIC": lambda: NoisyEnvironment(static_actions=True),
    "noisy STATIC scrambled": lambda: NoisyEnvironment(moves=SCRAMBLED, static_actions=True),
}

POLICIES = {
    "random": lambda: RandomAgent(seed=0),
    "v1 (frozen)": FrozenNavigator,
    "centroid": NavigatorAgent,
    "overlap": partial(NavigatorAgent, estimator="overlap"),
    "fallback *": partial(NavigatorAgent, estimator="fallback"),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-actions", type=int, default=400)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    table: dict[str, dict[str, dict]] = {}
    print(f"{'arena':<24}" + "".join(f"{name:>15}" for name in POLICIES))
    for arena, make in ARENAS.items():
        row = {}
        for name, policy in POLICIES.items():
            result = run_episode(policy(), make(), max_actions=args.max_actions)
            row[name] = {
                "levels": result.levels_completed,
                "of": result.total_levels,
                "actions": result.actions_used,
                "won": result.won,
            }
        table[arena] = row
        print(f"{arena:<24}" + "".join(
            f"{str(c['levels']) + '/' + str(c['of']) + ' in ' + str(c['actions']):>15}" for c in row.values()
        ))
    print("\n* the walker the submission uses (arcagi3.router.walker)")

    if args.json_out:
        args.json_out.write_text(json.dumps({"max_actions": args.max_actions, "arenas": table},
                                            indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
