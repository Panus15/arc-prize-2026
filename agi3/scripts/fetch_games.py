"""Download every public ARC-AGI-3 game to disk, once, for offline play.

Run this on a machine that can reach arcprize.org. The games arrive as source
files in the SDK's own layout, and after that everything — our agent, the
random floor, the official scorecard — runs with no network at all:

    python scripts/fetch_games.py                      # key from agi3/.env or ARC_API_KEY
    python scripts/fetch_games.py --out ~/arc-games

The files are ARC Prize's, not ours: keep them out of this public repository
(environment_files/ is gitignored). To hand them to someone, use a private
repository — see docs/YOUR-STEPS.md.

The key is read, used and never printed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

AGI3 = Path(__file__).resolve().parents[1]


def load_key() -> str:
    if os.environ.get("ARC_API_KEY"):
        return os.environ["ARC_API_KEY"]
    env_file = AGI3 / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "ARC_API_KEY":
                return value.strip().strip('"').strip("'")
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=AGI3 / "environment_files")
    args = parser.parse_args(argv)

    key = load_key()
    print(f"API key: {'found (' + str(len(key)) + ' characters)' if key else 'none - trying anonymous'}")

    from arc_agi import Arcade, OperationMode

    quiet = logging.getLogger("fetch_games")
    quiet.addHandler(logging.NullHandler())
    quiet.propagate = False

    args.out.mkdir(parents=True, exist_ok=True)
    try:
        arcade = Arcade(
            arc_api_key=key,
            operation_mode=OperationMode.NORMAL,
            environments_dir=str(args.out),
            recordings_dir=str(args.out / ".recordings"),
            logger=quiet,
        )
    except Exception as error:  # network, auth: say which, never the key
        print(f"could not reach the ARC API: {type(error).__name__}: {error}")
        return 1

    games = sorted({e.game_id.split("-")[0] for e in arcade.get_environments()})
    if not games:
        print("the API listed no games - run scripts/check_live.py to see whether it is the key or the network")
        return 1
    print(f"{len(games)} games listed; downloading into {args.out}")

    fetched, failed = [], []
    for game_id in games:
        env = arcade.make(game_id)
        (fetched if env is not None else failed).append(game_id)
        print(f"  {game_id}  {'ok' if env is not None else 'FAILED'}")

    manifest = sorted(str(p.relative_to(args.out)) for p in args.out.rglob("metadata.json"))
    (args.out / "MANIFEST.json").write_text(
        json.dumps({"games": fetched, "failed": failed, "metadata_files": manifest}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(fetched)} downloaded, {len(failed)} failed; manifest at {args.out / 'MANIFEST.json'}")
    print("next: docs/YOUR-STEPS.md, step 3")
    return 0 if fetched and not failed else 1


if __name__ == "__main__":
    sys.exit(main())
