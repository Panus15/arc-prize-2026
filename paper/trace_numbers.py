"""Check that every figure in the writeup appears in a measurement document.

The project's rule is that no number is typed in from memory: each one must
trace to a document recording the run that produced it. This finds every figure
in the shippable text of the writeup and looks for it in docs/*.md and the data
shipped with the paper. A figure found nowhere is reported, and the exit status
is non-zero.

A match only shows the figure exists somewhere in the record, not that it means
the same thing there; the report lists where each was found so that can be read.
Single-digit bare integers are skipped — "3 of 3" would match anything.

    python paper/trace_numbers.py            # untraced figures only
    python paper/trace_numbers.py --all      # and where each traced one was found
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DRAFT = HERE / "writeup-draft.md"
SOURCES = sorted((ROOT / "docs").glob("*.md")) + sorted((HERE / "data").glob("*.json"))

# 2,276 · 0.4% · −0.93 · 97–100% · 5.2 · 64×64
FIGURE = re.compile(r"[−-]?\d[\d,]*(?:\.\d+)?%?")


def shippable(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\*\(~?[^)]*\)\*", "", text)  # draft word-budget annotations
    lines = [line for line in text.splitlines() if not re.match(r"\s*>\s*[฀-๿]", line)]
    lines = [re.sub(r"^#+\s*\d+\.\s*", "", line) for line in lines]  # "## 4." section numbers
    return "\n".join(lines)


def variants(figure: str) -> set[str]:
    bare = figure.replace("−", "-")
    out = {figure, bare, bare.replace(",", ""), bare.lstrip("-")}
    if not bare.endswith("%"):
        out |= {v + "%" for v in list(out)}
    return {v for v in out if v}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)

    text = shippable(DRAFT.read_text(encoding="utf-8"))
    corpus = {path: path.read_text(encoding="utf-8").replace("−", "-") for path in SOURCES}
    figures = sorted({m.group(0).rstrip(",.") for m in FIGURE.finditer(text)},
                     key=lambda f: (len(f), f))
    figures = [f for f in figures if not re.fullmatch(r"-?\d", f)]

    untraced = []
    for figure in figures:
        where = [p.relative_to(ROOT) for p, body in corpus.items()
                 if any(re.search(rf"(?<![\d.]){re.escape(v)}(?![\d])", body) for v in variants(figure))]
        if not where:
            untraced.append(figure)
        elif args.all:
            print(f"{figure:>10}  {', '.join(str(w) for w in where[:3])}")

    print(f"{len(figures)} figures checked, {len(untraced)} untraced")
    for figure in untraced:
        print(f"  UNTRACED: {figure}")
    return 1 if untraced else 0


if __name__ == "__main__":
    sys.exit(main())
