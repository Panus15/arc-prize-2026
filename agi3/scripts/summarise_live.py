"""Summarise recordings from the official ARC-AGI-3-Agents runner.

The live game has never been reached from the development container, so the
run happens on someone else's machine and comes back as a directory of
`*.recording.jsonl` files.  This turns that directory into the handful of
numbers the writeup is waiting on, so nobody has to eyeball a trace and nobody
has to retype a figure.

    python scripts/summarise_live.py path/to/recordings
    python scripts/summarise_live.py path/to/recordings --json-out live.json

Each recorded line is `{"timestamp": ..., "data": {...}}` where data is either a
dumped FrameData or a scorecard.  FrameData counts progress in
`levels_completed` out of `win_levels` — not a score field — so that is what is
read here.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

WON = "WIN"


@dataclass
class GameSummary:
    game_id: str
    actions: int = 0
    levels_completed: int = 0
    win_levels: int = 0
    final_state: str = "UNKNOWN"
    resets: int = 0
    action_counts: Counter[int] = field(default_factory=Counter)

    @property
    def won(self) -> bool:
        return self.final_state == WON

    def line(self) -> str:
        target = self.win_levels or "?"
        verdict = "WIN " if self.won else "lost"
        return (
            f"{self.game_id:<10} {verdict} {self.levels_completed}/{target} levels "
            f"in {self.actions} actions"
        )


def read_recording(path: Path) -> GameSummary | None:
    summary: GameSummary | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw).get("data")
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "state" not in data:
            continue  # a scorecard line, not a frame

        if summary is None:
            summary = GameSummary(game_id=str(data.get("game_id", path.stem)))
        summary.final_state = str(data.get("state", summary.final_state))
        summary.levels_completed = int(data.get("levels_completed") or 0)
        summary.win_levels = int(data.get("win_levels") or summary.win_levels)
        if data.get("full_reset"):
            summary.resets += 1

        action = (data.get("action_input") or {}).get("id")
        if action is not None:
            summary.actions += 1
            summary.action_counts[int(action)] += 1
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("recordings", type=Path, help="directory of *.recording.jsonl")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    files = sorted(args.recordings.glob("*.recording.jsonl"))
    if not files:
        print(f"no *.recording.jsonl under {args.recordings}")
        return 2

    summaries = [s for s in (read_recording(f) for f in files) if s is not None]
    if not summaries:
        print("found recordings but no frames in them")
        return 2

    print(f"{len(summaries)} game(s)\n")
    for summary in summaries:
        print("  " + summary.line())

    won = sum(1 for s in summaries if s.won)
    levels = sum(s.levels_completed for s in summaries)
    actions = sum(s.actions for s in summaries)
    print(f"\ngames won      {won}/{len(summaries)}")
    print(f"levels cleared {levels}")
    print(f"actions spent  {actions}")

    # No verdict here on purpose: a recording has no floor to compare against,
    # and the mock's result only carries over as an ordering against random.
    print("\nfor the comparison with the calibrated mock, use scripts/play_offline.py")

    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {
                    "games": [
                        {
                            "game_id": s.game_id,
                            "final_state": s.final_state,
                            "levels_completed": s.levels_completed,
                            "win_levels": s.win_levels,
                            "actions": s.actions,
                            "resets": s.resets,
                            "action_counts": dict(sorted(s.action_counts.items())),
                        }
                        for s in summaries
                    ],
                    "totals": {
                        "games": len(summaries),
                        "games_won": won,
                        "levels_cleared": levels,
                        "actions": actions,
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nwrote {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
