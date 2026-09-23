"""Count the writeup the way the competition counts it.

The limit is 1,500 words and going over is penalised, so this has to be a
command anyone can re-run rather than a number somebody remembers.

What is counted: the title, the section headings, and the prose.
What is not: the Thai editorial comments (HTML comments, never shipped), the
draft word-budget annotations in headings, and the Thai "fill this in later"
blockquotes.  Code blocks are reported both ways, because it is not stated
whether a judge counts them.

    python paper/wordcount.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

LIMIT = 1500
RESERVED = 70  # §1 closing line and §8 result sentence, both waiting on the live run

DRAFT = Path(__file__).resolve().parent / "writeup-draft.md"


def strip(text: str, *, keep_code: bool) -> str:
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)  # Thai editorial notes
    if not keep_code:
        text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\*\(~?[^)]*\)\*", "", text)  # "*(~180 words)*" heading annotations
    text = "\n".join(
        line for line in text.splitlines() if not re.match(r"\s*>\s*[฀-๿]", line)
    )
    return text


def count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def main() -> int:
    raw = DRAFT.read_text(encoding="utf-8")
    prose = count(strip(raw, keep_code=False))
    with_code = count(strip(raw, keep_code=True))

    print(f"limit                    {LIMIT}")
    print(f"prose + headings         {prose}")
    print(f"  ... including code      {with_code}")
    print(f"reserved for live result  {RESERVED}")
    room = LIMIT - with_code - RESERVED
    print(f"headroom (worst case)     {room:+d}")

    if room < 0:
        print("\nOVER BUDGET — cut before adding the live result.")
        return 1
    print("\nwithin budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
