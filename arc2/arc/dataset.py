"""Loader and validator for the ARC-AGI-2 public task corpus.

The corpus lives in a separate, data-only repository
(https://github.com/arcprize/ARC-AGI-2, Apache-2.0). `setup.sh` / `setup.bat`
clone it beside this package as `ARC-AGI-2/`; nothing here vendors task files,
so the corpus stays a plain external checkout you can re-pull or re-pin.

Point `ARC_AGI_2_DATA` at any other `data/` directory to override the location.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SPLITS: tuple[str, ...] = ("training", "evaluation")

# Published composition of the public corpus (dataset readme, "Dataset composition").
EXPECTED_COUNTS: dict[str, int] = {"training": 1000, "evaluation": 120}

# Grid limits from the task spec: 1x1 up to 30x30, symbols 0-9.
MIN_DIM = 1
MAX_DIM = 30
MAX_SYMBOL = 9

Grid = list[list[int]]

_WORKSPACE = Path(__file__).resolve().parent.parent
_DEFAULT_DATA = _WORKSPACE / "ARC-AGI-2" / "data"


class DatasetNotFoundError(FileNotFoundError):
    """The ARC-AGI-2 checkout is missing or does not look like the dataset."""


class TaskFormatError(ValueError):
    """A task file does not match the documented ARC task schema."""


@dataclass(frozen=True)
class Pair:
    """One demonstration or test pair. `output` is None only if held out."""

    input: Grid
    output: Grid | None = None

    @property
    def input_shape(self) -> tuple[int, int]:
        return _shape(self.input)

    @property
    def output_shape(self) -> tuple[int, int] | None:
        return None if self.output is None else _shape(self.output)


@dataclass(frozen=True)
class Task:
    """A single ARC task: demonstration pairs plus test pair(s)."""

    task_id: str
    split: str
    train: tuple[Pair, ...]
    test: tuple[Pair, ...]

    @property
    def pairs(self) -> tuple[Pair, ...]:
        return self.train + self.test


def _shape(grid: Grid) -> tuple[int, int]:
    return len(grid), len(grid[0])


def data_root() -> Path:
    """Absolute path to the dataset's `data/` directory.

    Raises DatasetNotFoundError with recovery instructions if it is absent.
    """
    override = os.environ.get("ARC_AGI_2_DATA")
    root = Path(override).expanduser() if override else _DEFAULT_DATA
    if not root.is_dir():
        raise DatasetNotFoundError(
            f"ARC-AGI-2 data directory not found at {root}.\n"
            "Fetch the corpus with the workspace setup script "
            "(./setup.sh, or setup.bat on Windows), or clone it manually:\n"
            "  git clone --depth 1 https://github.com/arcprize/ARC-AGI-2.git\n"
            "Alternatively set ARC_AGI_2_DATA to an existing data/ directory."
        )
    return root.resolve()


def split_dir(split: str) -> Path:
    """Directory holding the task files for `split`."""
    if split not in SPLITS:
        raise ValueError(f"unknown split {split!r}; expected one of {', '.join(SPLITS)}")
    path = data_root() / split
    if not path.is_dir():
        raise DatasetNotFoundError(
            f"dataset at {data_root()} has no {split!r} split — the checkout looks incomplete"
        )
    return path


@cache
def task_ids(split: str) -> tuple[str, ...]:
    """Sorted task ids (filename stems) available in `split`."""
    return tuple(sorted(p.stem for p in split_dir(split).glob("*.json")))


def _validate_grid(grid: object, where: str) -> Grid:
    if not isinstance(grid, list) or not grid:
        raise TaskFormatError(f"{where}: grid must be a non-empty list of rows")

    width: int | None = None
    for r, row in enumerate(grid):
        if not isinstance(row, list) or not row:
            raise TaskFormatError(f"{where}: row {r} must be a non-empty list")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise TaskFormatError(
                f"{where}: grid is ragged — row {r} has {len(row)} cells, expected {width}"
            )
        for c, cell in enumerate(row):
            # bool is a subclass of int, and a True in a grid is always a bug.
            if isinstance(cell, bool) or not isinstance(cell, int):
                raise TaskFormatError(f"{where}: cell ({r},{c}) is {cell!r}, expected an int")
            if not 0 <= cell <= MAX_SYMBOL:
                raise TaskFormatError(
                    f"{where}: cell ({r},{c}) is {cell}, outside the 0-{MAX_SYMBOL} symbol range"
                )

    height, width = len(grid), width or 0
    if not (MIN_DIM <= height <= MAX_DIM and MIN_DIM <= width <= MAX_DIM):
        raise TaskFormatError(
            f"{where}: grid is {height}x{width}, outside the "
            f"{MIN_DIM}x{MIN_DIM}-{MAX_DIM}x{MAX_DIM} range"
        )
    return grid


def _parse_pairs(raw: object, where: str, *, require_output: bool) -> tuple[Pair, ...]:
    if not isinstance(raw, list) or not raw:
        raise TaskFormatError(f"{where}: expected a non-empty list of pairs")

    pairs: list[Pair] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise TaskFormatError(f"{where}[{i}]: expected an object with 'input'/'output'")
        if "input" not in item:
            raise TaskFormatError(f"{where}[{i}]: missing 'input'")
        grid_in = _validate_grid(item["input"], f"{where}[{i}].input")

        grid_out: Grid | None = None
        if "output" in item:
            grid_out = _validate_grid(item["output"], f"{where}[{i}].output")
        elif require_output:
            raise TaskFormatError(f"{where}[{i}]: missing 'output'")

        pairs.append(Pair(input=grid_in, output=grid_out))
    return tuple(pairs)


def parse_task(payload: object, task_id: str, split: str = "") -> Task:
    """Validate a decoded task payload and build a Task.

    Test outputs are optional so held-out formats parse; public split files
    always carry them, and `arc verify` asserts that.
    """
    if not isinstance(payload, dict):
        raise TaskFormatError(f"{task_id}: task file must contain a JSON object")
    for field in ("train", "test"):
        if field not in payload:
            raise TaskFormatError(f"{task_id}: missing {field!r}")

    return Task(
        task_id=task_id,
        split=split,
        train=_parse_pairs(payload["train"], f"{task_id}.train", require_output=True),
        test=_parse_pairs(payload["test"], f"{task_id}.test", require_output=False),
    )


def load_task_file(path: str | os.PathLike[str], split: str = "") -> Task:
    """Load and validate a single task JSON file."""
    path = Path(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskFormatError(f"{path}: invalid JSON — {exc}") from exc
    return parse_task(payload, task_id=path.stem, split=split)


def load_task(task_id: str, split: str = "training") -> Task:
    """Load one task by id from `split`."""
    path = split_dir(split) / f"{task_id}.json"
    if not path.is_file():
        raise DatasetNotFoundError(f"no task {task_id!r} in the {split} split ({path} missing)")
    return load_task_file(path, split=split)


def iter_split(split: str = "training") -> Iterator[Task]:
    """Yield every task in `split`, in sorted id order."""
    for task_id in task_ids(split):
        yield load_task(task_id, split)


def load_split(split: str = "training") -> list[Task]:
    """Eagerly load every task in `split`."""
    return list(iter_split(split))


def grid_shapes(tasks: Sequence[Task]) -> list[tuple[int, int]]:
    """Shapes of every grid across `tasks` — inputs and available outputs."""
    shapes: list[tuple[int, int]] = []
    for task in tasks:
        for pair in task.pairs:
            shapes.append(pair.input_shape)
            out_shape = pair.output_shape
            if out_shape is not None:
                shapes.append(out_shape)
    return shapes
