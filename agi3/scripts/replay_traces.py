"""Feed real recorded boards through the agent we submit: crashes, speed, routing.

Until the real game files arrive, the 500 recorded runs of the 25 public games
are the only real boards we have. They cannot say how well the agent plays —
the recorded actions were someone else's, so the agent's own choices are never
carried out — but they can say three things that matter on Kaggle:

  crashes   an exception inside choose_action ends that game's thread in the
            runner, which scores the whole game 0
  speed     the 12-hour limit is shared by every game, so the time per action
            on real boards decides how many actions each game can be given
  routing   whether each game goes to the walking or the clicking policy

Recordings carry no `available_actions`, so each game's action set is taken as
the union of the actions recorded across all of its passes.

    python scripts/replay_traces.py                    # one pass per game
    python scripts/replay_traces.py --passes 3 --json-out replay.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ActionInput

AGI3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGI3))

from arcagi3.clicker import ClickAgent  # noqa: E402
from arcagi3.navigator_v1 import NavigatorAgent as FrozenNavigator  # noqa: E402
from arcagi3.router import RoutingAgent  # noqa: E402
from arcagi3.sdk_adapter import SDKPolicyAdapter  # noqa: E402

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
BY_NAME = {action.name: action.value for action in GameAction}
STATES = {state.name: state for state in GameState}


class Probe(SDKPolicyAdapter):
    """The submitted agent's decision path, without a runner around it."""

    policy_factory = RoutingAgent
    survive_policy_errors = False  # this tool exists to find them


class FrozenProbe(Probe):
    """The same path with the walker frozen at dc949b4, for before/after."""

    policy_factory = staticmethod(lambda: RoutingAgent(walker=FrozenNavigator, clicker=ClickAgent))


PROBES = {"current": Probe, "v1": FrozenProbe}


def game_of(path: Path) -> str:
    return path.name.split("-")[0]


def offered_actions(paths: list[Path]) -> list[int]:
    """Every action any pass of this game recorded, plus RESET."""
    seen = {GameAction.RESET.value}
    for path in paths:
        for line in path.open(encoding="utf-8"):
            record = json.loads(line)
            if record.get("type") == "action" and record.get("action_name") in BY_NAME:
                seen.add(BY_NAME[record["action_name"]])
    return sorted(seen)


def frames_of(path: Path, available: list[int]):
    for line in path.open(encoding="utf-8"):
        record = json.loads(line)
        if record.get("type") not in ("initial", "action") or record.get("board") is None:
            continue
        yield FrameData(
            game_id=game_of(path),
            frame=[record["board"]],
            state=STATES.get(str(record.get("state")), GameState.NOT_FINISHED),
            levels_completed=int(record.get("score") or 0),
            win_levels=0,
            action_input=ActionInput(id=GameAction.RESET, data={}),
            guid=None,
            full_reset=False,
            available_actions=available,
        )


def replay(path: Path, available: list[int], probe: type[Probe] = Probe) -> dict:
    agent = probe()
    frames: list[FrameData] = []
    timings: list[float] = []
    chosen_actions: Counter[str] = Counter()
    error: str | None = None
    for frame in frames_of(path, available):
        frames.append(frame)
        start = time.perf_counter()
        try:
            action = agent.choose_action(frames, frame)
        except Exception:  # the point is to find these
            error = traceback.format_exc(limit=6)
            break
        timings.append(time.perf_counter() - start)
        chosen_actions[action.name] += 1
        if action.value not in available:
            error = f"chose {action.name}, which the game never offered ({available})"
            break
    chosen = agent.policy.chosen
    return {
        "file": path.name,
        "frames": len(frames),
        "policy": chosen.name if chosen is not None else "undecided",
        "timings": timings,
        "actions": chosen_actions,
        "error": error,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path(DEFAULT_TRACES))
    parser.add_argument("--passes", type=int, default=1, help="passes replayed per game")
    parser.add_argument("--walker", choices=sorted(PROBES), default="current",
                        help="current: what is submitted; v1: the walker frozen at dc949b4")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    probe = PROBES[args.walker]

    by_game: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(args.traces.glob("*_events.jsonl")):
        by_game[game_of(path)].append(path)
    if not by_game:
        print(f"no *_events.jsonl under {args.traces}")
        return 2

    rows, crashes, all_times = [], [], []
    for game, paths in sorted(by_game.items()):
        available = offered_actions(paths)
        results = [replay(path, available, probe) for path in paths[: args.passes]]
        times = [t for r in results for t in r["timings"]]
        pressed = sum((r["actions"] for r in results), Counter())
        decisions = sum(pressed.values())
        all_times += times
        for r in results:
            if r["error"]:
                crashes.append({"game": game, "file": r["file"], "error": r["error"]})
        rows.append(
            {
                "game": game,
                "offered": available,
                "policy": sorted({r["policy"] for r in results}),
                "frames": sum(r["frames"] for r in results),
                "median_ms": 1000 * statistics.median(times) if times else None,
                "p99_ms": 1000 * sorted(times)[int(0.99 * (len(times) - 1))] if times else None,
                "max_ms": 1000 * max(times) if times else None,
                "crashed": sum(1 for r in results if r["error"]),
                "action5_share": pressed["ACTION5"] / decisions if decisions else None,
                "actions": dict(sorted(pressed.items())),
            }
        )

    print(f"walker: {args.walker}\n")
    print(f"{'game':<6} {'offered':<22} {'policy':<11} {'frames':>6} "
          f"{'med ms':>7} {'p99 ms':>7} {'max ms':>7} {'ACTION5':>8}  crash")
    for row in rows:
        fmt = lambda v: f"{v:7.1f}" if v is not None else "      -"  # noqa: E731
        share = row["action5_share"]
        a5 = f"{share:8.0%}" if share is not None else "       -"
        print(f"{row['game']:<6} {str(row['offered']):<22} {','.join(row['policy']):<11} "
              f"{row['frames']:>6} {fmt(row['median_ms'])} {fmt(row['p99_ms'])} "
              f"{fmt(row['max_ms'])} {a5}  {row['crashed'] or ''}")

    if all_times:
        ordered = sorted(all_times)
        print(f"\nall games: {len(all_times)} decisions, median {1000 * statistics.median(ordered):.1f} ms, "
              f"p99 {1000 * ordered[int(0.99 * (len(ordered) - 1))]:.1f} ms, "
              f"max {1000 * ordered[-1]:.1f} ms")
    print(f"crashes: {len(crashes)} of {sum(min(len(p), args.passes) for p in by_game.values())} passes")
    for crash in crashes[:5]:
        print(f"\n--- {crash['game']} ({crash['file']}) ---\n{crash['error']}")

    if args.json_out:
        args.json_out.write_text(
            json.dumps({"walker": args.walker, "passes_per_game": args.passes, "games": rows,
                        "crashes": crashes},
                       indent=2) + "\n",
            encoding="utf-8",
        )
    return 1 if crashes else 0


if __name__ == "__main__":
    raise SystemExit(main())
