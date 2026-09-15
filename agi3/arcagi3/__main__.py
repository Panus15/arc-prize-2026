"""Command line entry point: `python -m arcagi3 <command>`."""

from __future__ import annotations

import argparse
import sys

from arcagi3.agent import BaseAgent, GreedyAgent, RandomAgent
from arcagi3.budget import run_episode
from arcagi3.click_mock import ClickEnvironment
from arcagi3.clicker import ClickAgent
from arcagi3.explorer import ExplorerAgent
from arcagi3.navigator import NavigatorAgent

AGENTS: dict[str, type[BaseAgent]] = {
    "random": RandomAgent,
    "greedy": GreedyAgent,
    "explorer": ExplorerAgent,
    "navigator": NavigatorAgent,
    "clicker": ClickAgent,
}


def _play(args: argparse.Namespace) -> int:
    names = list(AGENTS) if args.agent == "all" else [args.agent]
    for name in names:
        agent = AGENTS[name](args.seed) if name == "random" else AGENTS[name]()
        # The clicker plays the click-driven games; the walkers cannot, and it
        # cannot play theirs, so each is run against the board it is built for.
        env = ClickEnvironment() if name == "clicker" else None
        print(run_episode(agent, env, max_actions=args.max_actions).summary())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arcagi3", description="ARC-AGI-3 offline harness")
    sub = parser.add_subparsers(dest="command", required=True)

    play = sub.add_parser("play", help="run an agent against the offline environment")
    play.add_argument("--agent", choices=[*AGENTS, "all"], default="all")
    play.add_argument("--seed", type=int, default=0, help="seed for the random agent")
    play.add_argument("--max-actions", type=int, default=500)
    play.set_defaults(func=_play)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
