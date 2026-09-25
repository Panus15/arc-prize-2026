"""Which action cleared each level, in the recorded runs of the 25 public games.

Routing by what a game offers assumes the offer says how the game is played.
The recordings can check that: every level completion is tagged with the action
that produced it. A game that offers directions but is only ever cleared by a
click, or cleared only by ACTION5, is a game the offer misdescribes.

These are one harness's runs, so they say which actions *can* clear levels, not
which are best. The games are the public set; the hidden set is different, so
nothing here is used as a per-game rule — only as evidence for general ones.

    python scripts/completion_actions.py
    python scripts/completion_actions.py --json-out completions.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
DIRECTIONS = {"ACTION1", "ACTION2", "ACTION3", "ACTION4"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path(DEFAULT_TRACES))
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    by_game: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(args.traces.glob("*_events.jsonl")):
        by_game[path.name.split("-")[0]].append(path)
    if not by_game:
        print(f"no *_events.jsonl under {args.traces}")
        return 2

    rows = []
    print(f"{'game':<6}{'offers':<8}{'actions':>8}{'click':>7}{'dir':>6}{'A5':>5}   cleared by")
    for game, paths in sorted(by_game.items()):
        pressed: Counter[str] = Counter()
        cleared: Counter[str] = Counter()
        for path in paths:
            for line in path.open(encoding="utf-8"):
                record = json.loads(line)
                if record.get("type") != "action":
                    continue
                pressed[record.get("action_name")] += 1
                if record.get("level_completed"):
                    cleared[record.get("action_name")] += 1
        total = sum(pressed.values())
        offers = ("D" if pressed.keys() & DIRECTIONS else "") + ("5" if pressed["ACTION5"] else "") + (
            "C" if pressed["ACTION6"] else ""
        )
        walk_offered = bool(pressed.keys() & DIRECTIONS)
        by_click = cleared["ACTION6"]
        by_a5 = cleared["ACTION5"]
        note = ""
        if walk_offered and cleared and by_click == sum(cleared.values()):
            note = "  <- offers directions, cleared only by clicks"
        elif cleared and by_a5 == sum(cleared.values()):
            note = "  <- cleared only by ACTION5"
        rows.append({"game": game, "offers": offers, "actions": total, "cleared_by": dict(cleared),
                     "click_share": pressed["ACTION6"] / total, "direction_share":
                     sum(pressed[d] for d in DIRECTIONS) / total, "action5_share": pressed["ACTION5"] / total})
        by = ", ".join(f"{k.replace('ACTION', 'A')}:{v}" for k, v in cleared.most_common()) or "-"
        print(f"{game:<6}{offers:<8}{total:>8}{pressed['ACTION6'] / total:>7.0%}"
              f"{sum(pressed[d] for d in DIRECTIONS) / total:>6.0%}{pressed['ACTION5'] / total:>5.0%}   {by}{note}")

    if args.json_out:
        args.json_out.write_text(json.dumps({"games": rows}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
