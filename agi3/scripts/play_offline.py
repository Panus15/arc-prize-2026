"""Play our agent against real ARC-AGI-3 games, offline, the way Kaggle scores it.

The competition engine runs games from source files on disk; Kaggle's rerun
does exactly that with the hidden set. Given a directory of downloaded public
games (see scripts/fetch_games.py), this plays them with no network at all,
through the official runner's own Agent loop, and reads the official scorecard.

Two agents are played on identical games so the numbers mean something:

    myagent  what we submit (submission/my_agent.py)
    random   a seeded uniform-random policy behind the same adapter — the floor

    scripts/vendor_framework.sh                          # once: fetch the runner
    python scripts/play_offline.py path/to/environment_files --json-out live.json
    python scripts/play_offline.py path/to/environment_files --games ls20,vc33

Games are played one at a time, not on threads, so a run is repeatable.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import tempfile
from pathlib import Path

AGI3 = Path(__file__).resolve().parents[1]
RUNNER = AGI3 / "vendor" / "ARC-AGI-3-Agents"

# What the noise-calibrated mock said (docs/simulation-gap.md, commit 4af7cf0):
# seeded random cleared 2/3, our navigator 0/3. The games differ, so only the
# ordering carries over. The writeup (section 6) predicts a further gap between
# that environment and real games: a reversed ordering would be that gap, an
# unchanged one would count against the prediction.
MOCK = {"random": 2, "navigator": 0, "levels": 3}


def load_agents(max_actions: int) -> dict[str, type]:
    if not (RUNNER / "agents" / "agent.py").exists():
        raise SystemExit(f"runner not found at {RUNNER} — run scripts/vendor_framework.sh first")
    for path in (AGI3, AGI3 / "submission", RUNNER):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    from agents.agent import Agent
    from my_agent import MyAgent

    from arcagi3.agent import RandomAgent
    from arcagi3.sdk_adapter import SDKPolicyAdapter

    class RandomFloor(SDKPolicyAdapter, Agent):
        policy_factory = staticmethod(lambda: RandomAgent(seed=0))
        is_done = MyAgent.is_done

    MyAgent.MAX_ACTIONS = RandomFloor.MAX_ACTIONS = max_actions
    return {"myagent": MyAgent, "random": RandomFloor}


def play(arcade, agent_class, name: str, games: list[str]) -> dict:
    card = arcade.open_scorecard(tags=[name])
    per_game = []
    for game_id in games:
        env = arcade.make(game_id, scorecard_id=card)
        if env is None:
            per_game.append({"game_id": game_id, "error": "could not create environment"})
            continue
        agent = agent_class(
            card_id=card,
            game_id=game_id,
            agent_name=f"{name}.offline",
            ROOT_URL="http://localhost",
            record=False,
            arc_env=env,
            tags=[name],
        )
        agent.main()
        final = agent.frames[-1]
        router = getattr(agent, "policy", None)
        used = list(getattr(router, "used", None) or [name])
        per_game.append(
            {
                "game_id": game_id,
                # The policy the game started with: what "walked games" means in
                # the pre-registered comparison. `used` shows any switch after.
                "policy": used[0],
                "used": used,
                "state": final.state.name,
                "levels_completed": final.levels_completed,
                "win_levels": final.win_levels,
                "actions": agent.action_counter,
            }
        )
    scorecard = arcade.close_scorecard(card)
    return {"score": scorecard.score if scorecard else None, "games": per_game}


def compare_with_mock(results: dict) -> dict:
    """Does random still beat our walker on real walked games, as on the mock?"""
    ours_by_game = {g["game_id"]: g for g in results["myagent"]["games"] if "error" not in g}
    walked = [gid for gid, g in ours_by_game.items() if g["policy"] == "navigator"]
    floor = {g["game_id"]: g for g in results["random"]["games"] if "error" not in g}
    ours = sum(ours_by_game[g]["levels_completed"] for g in walked)
    random_levels = sum(floor[g]["levels_completed"] for g in walked if g in floor)
    if not walked:
        outcome = "no walked games - nothing to compare"
    elif ours == random_levels:
        outcome = "tied - no evidence either way"
    elif random_levels > ours:
        outcome = "held - random still ahead, as on the mock (counts against a further gap)"
    else:
        outcome = "REVERSED - our walker ahead of random (the further gap section 6 predicts)"
    return {"walked_games": len(walked), "ours": ours, "random": random_levels,
            "outcome": outcome, "mock": MOCK}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("environments", type=Path, help="directory of downloaded games")
    parser.add_argument("--games", help="comma-separated ids; default is every game found")
    parser.add_argument("--max-actions", type=int, default=400)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    from arc_agi import Arcade, OperationMode

    agents = load_agents(args.max_actions)
    quiet = logging.getLogger("play_offline")
    quiet.addHandler(logging.NullHandler())
    quiet.propagate = False
    logging.getLogger().setLevel(logging.WARNING)

    with tempfile.TemporaryDirectory() as recordings:
        arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(args.environments),
            recordings_dir=recordings,
            logger=quiet,
        )
        found = sorted({e.game_id.split("-")[0] for e in arcade.get_environments()})
        if not found:
            print(f"no games under {args.environments}")
            return 2
        games = found
        if args.games:
            wanted = [g.strip().split("-")[0] for g in args.games.split(",") if g.strip()]
            missing = sorted(set(wanted) - set(found))
            if missing:
                print(f"not found: {missing}; available: {found}")
                return 2
            games = wanted

        results = {name: play(arcade, cls, name, games) for name, cls in agents.items()}

    print(f"{len(games)} game(s), max {args.max_actions} actions each\n")
    print(f"{'game':<8}" + "".join(f"{name:>22}" for name in results))
    for index, game_id in enumerate(games):
        cells = []
        for result in results.values():
            row = result["games"][index]
            if "error" in row:
                cells.append(f"{'error':>22}")
            else:
                cell = f"{row['levels_completed']}/{row['win_levels']} in {row['actions']}"
                cells.append(f"{cell:>22}")
        print(f"{game_id:<8}" + "".join(cells))

    print()
    for name, result in results.items():
        levels = sum(r.get("levels_completed", 0) for r in result["games"])
        print(f"{name:<8} levels cleared {levels:>4}   scorecard {result['score']}")

    comparison = compare_with_mock(results)
    print(
        f"\ncalibrated mock: random {MOCK['random']}/{MOCK['levels']}, "
        f"navigator {MOCK['navigator']}/{MOCK['levels']} - random ahead"
    )
    print(
        f"walked games here ({comparison['walked_games']}): "
        f"ours {comparison['ours']} levels, random {comparison['random']}"
    )
    print(f"ordering: {comparison['outcome']}  (only the ordering compares; the games differ)")

    if args.json_out:
        payload = {
            "max_actions": args.max_actions,
            "games": games,
            "results": results,
            "mock_comparison": comparison,
        }
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
