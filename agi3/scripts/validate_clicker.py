"""Would the click policy's learning rule pick the colour that actually works?

The click signal was checked against recorded games and the weights were
changed because of it. What has not been checked is the rule those weights feed:
given the outcomes a real game actually produced, does the policy end up
preferring the colour that completes levels?

This replays the recorded click-driven games, feeds each click's colour and
outcome through the same scoring the policy uses, and compares the colour it
would settle on against the colour that in fact completed the most levels. No
game is played — the policy never chose these clicks — so this tests the
learning rule, not the policy.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

from arcagi3.clicker import LEVEL_REWARD

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
CLICK_GAMES = ("ft09", "lp85", "r11l", "s5i5", "sb26", "su15", "tn36", "vc33")
MOUSE = re.compile(r"MOUSE\(row=(\d+),\s*col=(\d+)\)")


def clicks_in(path: str) -> list[tuple[int, bool, bool]]:
    """(colour under the click, did a level complete, did the board move)."""
    out: list[tuple[int, bool, bool]] = []
    previous: list[list[int]] | None = None
    for line in Path(path).open(encoding="utf-8"):
        record = json.loads(line)
        board = record.get("board")
        if record.get("type") == "action" and previous is not None and board is not None:
            match = MOUSE.match(str(record.get("action_display", "")))
            if match:
                row, col = int(match.group(1)), int(match.group(2))
                if 0 <= row < len(previous) and 0 <= col < len(previous[0]):
                    out.append(
                        (
                            previous[row][col],
                            bool(record.get("level_completed")),
                            bool(record.get("board_changed")),
                        )
                    )
        if board is not None:
            previous = board
    return out


def preferred_colour(clicks: list[tuple[int, bool, bool]]) -> int | None:
    """The colour the policy's scoring would settle on.

    Mirrors ClickAgent: a completed level is worth LEVEL_REWARD, a board that
    did not move at all counts against, and a board that merely changed counts
    for nothing — which is what the recorded games forced.
    """
    score: Counter[int] = Counter()
    for colour, completed, changed in clicks:
        if completed:
            score[colour] += LEVEL_REWARD
        elif not changed:
            score[colour] -= 1
    best = [colour for colour, value in score.items() if value == max(score.values(), default=0)]
    return min(best) if best and max(score.values(), default=0) > 0 else None


def truth_colour(clicks: list[tuple[int, bool, bool]]) -> int | None:
    """The colour that in fact completed the most levels."""
    completions: Counter[int] = Counter()
    for colour, completed, _ in clicks:
        if completed:
            completions[colour] += 1
    return completions.most_common(1)[0][0] if completions else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the click learning rule")
    parser.add_argument("--traces", default=DEFAULT_TRACES)
    parser.add_argument("--passes", type=int, default=6, help="passes per game to pool")
    args = parser.parse_args(argv)

    print(f"{'game':<8} {'clicks':>7} {'levels':>7} {'picked':>8} {'truth':>7} {'match':>7}")
    print("-" * 50)
    agreed = judged = 0
    for game in CLICK_GAMES:
        files = sorted(glob.glob(f"{args.traces}/{game}-*_p*_events.jsonl"))[: args.passes]
        if not files:
            print(f"{game:<8} {'(no traces)':>7}", file=sys.stderr)
            continue
        pooled: list[tuple[int, bool, bool]] = []
        for path in files:
            pooled.extend(clicks_in(path))
        levels = sum(1 for _, completed, _ in pooled if completed)
        picked, actual = preferred_colour(pooled), truth_colour(pooled)
        if actual is not None:
            judged += 1
            agreed += picked == actual
        verdict = "-" if actual is None else ("yes" if picked == actual else "no")
        print(
            f"{game:<8} {len(pooled):>7} {levels:>7} "
            f"{str(picked if picked is not None else '-'):>8} "
            f"{str(actual if actual is not None else '-'):>7} {verdict:>7}"
        )

    print("-" * 50)
    if judged:
        print(f"the rule picked the level-completing colour in {agreed}/{judged} games")
    else:
        print("no game completed a level; nothing to judge against")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
