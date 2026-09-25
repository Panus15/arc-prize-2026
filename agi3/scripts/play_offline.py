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

# Prediction recorded in the writeup before any real game was played: the
# policies that clear nothing on the noise-calibrated mock clear nothing live.
PREDICTED_LEVELS = 0


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
        per_game.append(
            {
                "game_id": game_id,
                "state": final.state.name,
                "levels_completed": final.levels_completed,
                "win_levels": final.win_levels,
                "actions": agent.action_counter,
            }
        )
    scorecard = arcade.close_scorecard(card)
    return {"score": scorecard.score if scorecard else None, "games": per_game}


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

    ours = sum(r.get("levels_completed", 0) for r in results["myagent"]["games"])
    print(f"\nprediction on record: {PREDICTED_LEVELS} levels for our agent on real games")
    if ours <= PREDICTED_LEVELS:
        print("outcome: prediction held")
    else:
        print(f"outcome: PREDICTION FAILED — our agent cleared {ours}")

    if args.json_out:
        payload = {
            "max_actions": args.max_actions,
            "games": games,
            "results": results,
            "prediction": {"levels": PREDICTED_LEVELS, "observed": ours},
        }
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
