"""Draw the cover image for the Paper Track submission.

Every number on the chart is read from paper/data/simulation-gap-measured.json,
which scripts/simulation_gap.py wrote.  Nothing here is typed in by hand.

    python paper/make_cover.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "simulation-gap-measured.json"
OUT = HERE / "cover.png"

QUIET = "quiet mock"
NOISY = "noise-calibrated mock"

LEARNS = {"random": "no learning", "greedy": "hard-coded", "explorer": "learns", "navigator": "learns"}

QUIET_COLOUR = "#9aa8bd"
NOISY_COLOUR = "#1f6fb4"
ZERO_COLOUR = "#9e1b1b"
INK = "#1b2330"
MUTED = "#5a6676"


def levels_cleared(cell: str) -> int:
    """'WIN 3/3 in 30' -> 3;  'lost 2/3 in 400' -> 2."""
    match = re.search(r"(\d+)/(\d+)", cell)
    if match is None:
        raise ValueError(f"cannot read a level count out of {cell!r}")
    return int(match.group(1))


def main() -> int:
    arenas = json.loads(DATA.read_text(encoding="utf-8"))["arenas"]
    policies = list(arenas)
    quiet = [levels_cleared(arenas[p][QUIET]) for p in policies]
    noisy = [levels_cleared(arenas[p][NOISY]) for p in policies]
    total = int(re.search(r"\d+/(\d+)", arenas[policies[0]][QUIET]).group(1))

    fig, ax = plt.subplots(figsize=(15, 8.3), dpi=100)
    fig.subplots_adjust(top=0.74, bottom=0.16, left=0.09, right=0.97)
    fig.patch.set_facecolor("white")

    positions = range(len(policies))
    width = 0.42
    ax.bar([p - width / 2 for p in positions], quiet, width, color=QUIET_COLOUR, label="quiet simulator")
    ax.bar([p + width / 2 for p in positions], noisy, width, color=NOISY_COLOUR,
           label="noise measured from real games")

    for pos, value in zip(positions, quiet, strict=True):
        ax.text(pos - width / 2, value + 0.1, str(value), ha="center", fontsize=17, color=MUTED)
    for pos, value in zip(positions, noisy, strict=True):
        colour = ZERO_COLOUR if value == 0 else NOISY_COLOUR
        weight = "bold" if value == 0 else "normal"
        ax.text(pos + width / 2, value + 0.1, str(value), ha="center", fontsize=17,
                color=colour, fontweight=weight)

    ax.set_xticks(list(positions))
    ax.set_xticklabels([f"{p}\n({LEARNS[p]})" for p in policies], fontsize=17, color=INK)
    ax.set_ylabel(f"levels cleared (of {total})", fontsize=16, color=INK)
    ax.set_ylim(0, total + 1.2)
    ax.set_yticks(range(total + 1))
    ax.tick_params(axis="y", labelsize=16, colors=INK)
    ax.tick_params(axis="x", length=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color="#e8ecf1", linewidth=1)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, fontsize=17)

    fig.text(0.09, 0.90, "Noise defeats only the policies that learn",
             fontsize=31, fontweight="bold", color=INK, va="center")
    fig.text(0.09, 0.845, "Same policies, two arenas. On a board carrying the noise real boards carry,",
             fontsize=19, color=MUTED, va="center")
    fig.text(0.09, 0.805, "random play beats both of our deliberate policies.",
             fontsize=19, color=MUTED, va="center")
    fig.text(0.09, 0.045, "ARC Prize 2026 · Paper Track · github.com/Panus15/arc-prize-2026",
             fontsize=15, color="#94a3b4", va="center")

    fig.savefig(OUT, facecolor="white")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
