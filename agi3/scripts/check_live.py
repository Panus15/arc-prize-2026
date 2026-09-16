"""Check a live ARC-AGI-3 connection, and optionally play one game.

Everything in this repository has been developed against offline environments
and recorded runs. Nothing has ever touched the live server, which makes "does
it actually work" the single largest open risk. This script closes it.

It is meant to be run on a machine with network access to arcprize.org. The
development container's egress policy blocks that domain, so this cannot be run
from there.

Read-only by default: it verifies the key and lists the games without touching a
scorecard. Playing a game consumes a scorecard entry, so it takes an explicit
--play flag and a named game.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BASE_URL = "https://three.arcprize.org"


def load_key(explicit: str | None) -> str | None:
    """The API key from --key, the environment, or a .env beside the workspace."""
    if explicit:
        return explicit
    if os.environ.get("ARC_API_KEY"):
        return os.environ["ARC_API_KEY"]

    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ARC_API_KEY":
                return value.strip().strip('"').strip("'")
    return None


def check_connection(key: str, base_url: str) -> list[dict] | None:
    """List the games the key can reach. Read-only: no scorecard is opened."""
    import requests

    try:
        response = requests.get(f"{base_url}/api/games", headers={"X-API-Key": key}, timeout=30)
    except requests.exceptions.RequestException as error:
        print(f"could not reach {base_url}: {type(error).__name__}: {error}", file=sys.stderr)
        return None

    if response.status_code == 401:
        print("the server rejected the key (401)", file=sys.stderr)
        return None
    if not response.ok:
        print(f"HTTP {response.status_code}: {response.text[:300]}", file=sys.stderr)
        return None
    return response.json()


def play_one(key: str, base_url: str, game_id: str, max_actions: int) -> int:
    """Play a single game with our policy. Consumes one scorecard entry."""
    from arc_agi import EnvironmentWrapper  # noqa: F401  (import check only)

    print(
        "Playing a live game needs the official ARC-AGI-3-Agents harness, which is\n"
        "not vendored here. Use arcagi3.sdk_adapter.SDKPolicyAdapter inside that\n"
        "repo's Agent subclass — see its module docstring — and run:\n"
        f"    uv run main.py --agent=<your agent> --game={game_id}\n"
        f"(max actions intended: {max_actions})",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a live ARC-AGI-3 connection")
    parser.add_argument("--key", help="API key; defaults to ARC_API_KEY or agi3/.env")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--play", metavar="GAME_ID", help="play this game (uses a scorecard)")
    parser.add_argument("--max-actions", type=int, default=100)
    args = parser.parse_args(argv)

    key = load_key(args.key)
    if not key:
        print("no API key found: pass --key, set ARC_API_KEY, or write agi3/.env", file=sys.stderr)
        return 2
    # Never print the key itself — this output gets pasted into chats and issues.
    print(f"key loaded ({len(key)} characters)")

    games = check_connection(key, args.base_url)
    if games is None:
        return 1

    print(f"connection OK — {len(games)} games reachable")
    for game in games:
        print(f"  {game.get('game_id')}")

    if args.play:
        return play_one(key, args.base_url, args.play, args.max_actions)
    print("\nread-only check only; pass --play GAME_ID to actually play one")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
