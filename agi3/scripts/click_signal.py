"""Failure two, reproduced: what a click tells you on the recorded real games.

The click policy was built on a signal that was decisive in our own click game:
a wrong click left the board still. This measures, on the recorded runs of the
eight click-only public games (first six passes each, as originally measured):

  changed   how often any click changes the board at all — the old signal
  cleared   how often a click completes a level — the one that discriminates
  lift      how much more often the best colour completes a level than the
            game's average click, among colours clicked at least 5 times

A click's target colour is read off the board before the click, at the recorded
MOUSE(row, col).

    python scripts/click_signal.py
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
CLICK_GAMES = ("ft09", "lp85", "r11l", "s5i5", "sb26", "su15", "tn36", "vc33")
MOUSE = re.compile(r"MOUSE\(row=(\d+),\s*col=(\d+)\)")
PASSES = 6
MIN_CLICKS = 5


def clicks(path: Path):
    """(colour clicked, board changed, level completed) for each recorded click."""
    previous = None
    for line in path.open(encoding="utf-8"):
        record = json.loads(line)
        board = record.get("board")
        if record.get("type") == "action" and previous is not None and board is not None:
            match = MOUSE.match(str(record.get("action_display", "")))
            if match:
                row, col = int(match.group(1)), int(match.group(2))
                if 0 <= row < len(previous) and 0 <= col < len(previous[0]):
                    yield previous[row][col], bool(record.get("board_changed")), bool(
                        record.get("level_completed")
                    )
        if board is not None:
            previous = board


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--traces", type=Path, default=Path(DEFAULT_TRACES))
    args = parser.parse_args(argv)

    print(f"{'game':<6}{'clicks':>8}{'changed':>9}{'cleared':>9}   best colour at clearing")
    total = cleared_total = 0
    lifts = []
    for game in CLICK_GAMES:
        per_colour: dict[int, list[int]] = defaultdict(lambda: [0, 0])
        n = changed = cleared = 0
        for path in sorted(args.traces.glob(f"{game}-*_p*_events.jsonl"))[:PASSES]:
            for colour, did_change, did_clear in clicks(path):
                n += 1
                changed += did_change
                cleared += did_clear
                per_colour[colour][0] += 1
                per_colour[colour][1] += did_clear
        if not n:
            continue
        total += n
        cleared_total += cleared
        ranked = sorted(((k / c, colour, c, k) for colour, (c, k) in per_colour.items()
                         if c >= MIN_CLICKS and k > 0), reverse=True)
        base = cleared / n
        best = "none clears a level"
        if ranked:
            rate, colour, c, k = ranked[0]
            best = f"colour {colour}: {k}/{c} = {rate:.1%}"
            lifts.append(rate / base)
        print(f"{game:<6}{n:>8}{changed / n:>9.0%}{base:>9.1%}   {best}")

    print(f"\n{total:,} clicks; {cleared_total / total:.1%} complete a level")
    if lifts:
        print(f"best colour clears levels {sum(lifts) / len(lifts):.1f}x as often as the average click")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
