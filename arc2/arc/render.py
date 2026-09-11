"""Terminal rendering for ARC grids — ANSI colour, no third-party dependencies."""

from __future__ import annotations

import os
import sys

from arc.dataset import Grid, Pair, Task

# The ten ARC symbols as they appear in the official testing interface.
SYMBOL_NAMES: tuple[str, ...] = (
    "black",
    "blue",
    "red",
    "green",
    "yellow",
    "grey",
    "fuchsia",
    "orange",
    "teal",
    "maroon",
)

# xterm-256 approximations of that palette, indexed by symbol.
_ANSI256: tuple[int, ...] = (16, 32, 203, 40, 220, 248, 200, 208, 117, 88)

_BLOCK = "  "  # two spaces on a coloured background keeps cells roughly square
_RESET = "\033[0m"


def supports_colour(stream: object | None = None) -> bool:
    """True when ANSI colour is safe to emit on `stream` (default: stdout)."""
    stream = stream if stream is not None else sys.stdout
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") is not None:
        return True
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def _cell(symbol: int, colour: bool) -> str:
    if not colour:
        return f"{symbol} "
    return f"\033[48;5;{_ANSI256[symbol]}m{_BLOCK}{_RESET}"


def render_grid(grid: Grid, *, colour: bool | None = None, indent: str = "") -> str:
    """Render one grid as text. `colour=None` auto-detects terminal support."""
    use_colour = supports_colour() if colour is None else colour
    return "\n".join(indent + "".join(_cell(c, use_colour) for c in row) for row in grid)


def _side_by_side(left: str, right: str, gap: str = "   ") -> str:
    """Join two rendered blocks column-wise, padding the shorter one."""
    lrows, rrows = left.split("\n"), right.split("\n")
    # Padding uses the *visible* width, which for a colour block is 2 chars per cell.
    width = max((_visible_width(r) for r in lrows), default=0)
    height = max(len(lrows), len(rrows))
    lines = []
    for i in range(height):
        lrow = lrows[i] if i < len(lrows) else ""
        rrow = rrows[i] if i < len(rrows) else ""
        lines.append(lrow + " " * (width - _visible_width(lrow)) + gap + rrow)
    return "\n".join(lines)


def _visible_width(line: str) -> int:
    """Length of `line` ignoring ANSI escape sequences."""
    width, i = 0, 0
    while i < len(line):
        if line[i] == "\033":
            end = line.find("m", i)
            i = len(line) if end == -1 else end + 1
            continue
        width += 1
        i += 1
    return width


def render_pair(pair: Pair, *, label: str = "", colour: bool | None = None) -> str:
    """Render one pair as `input -> output`, side by side."""
    left = render_grid(pair.input, colour=colour)
    if pair.output is None:
        body = _side_by_side(left, "(output held out)")
    else:
        body = _side_by_side(left, render_grid(pair.output, colour=colour))
    if not label:
        return body
    h_in, w_in = pair.input_shape
    out_shape = pair.output_shape
    dims = f"{h_in}x{w_in}" + (f" -> {out_shape[0]}x{out_shape[1]}" if out_shape else "")
    return f"{label}  ({dims})\n{body}"


def render_task(task: Task, *, colour: bool | None = None) -> str:
    """Render a whole task: every demonstration pair, then the test pair(s)."""
    blocks = [f"task {task.task_id}" + (f"  [{task.split}]" if task.split else "")]
    for i, pair in enumerate(task.train):
        blocks.append(render_pair(pair, label=f"train {i}", colour=colour))
    for i, pair in enumerate(task.test):
        blocks.append(render_pair(pair, label=f"test {i}", colour=colour))
    return "\n\n".join(blocks)
