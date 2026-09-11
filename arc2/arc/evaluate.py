"""Official-rules scoring harness for ARC-AGI-2.

The competition's definition of a point, implemented literally:

* a solver may propose at most `MAX_ATTEMPTS` (2) grids per test input;
* a test input is correct when *any* attempt equals the expected grid exactly —
  same row count, same column count, every cell equal;
* a task scores only when *every* one of its test inputs is correct. Most tasks
  have one test input, but some have up to four, and there is no partial credit.

Score = solved tasks / tasks evaluated.

A run is meant to be citable, so `EvalResult` carries provenance (solver, split,
UTC timestamp, git commit, interpreter) alongside the per-task records, and
`to_json()` writes the lot. Solver failures are data, not accidents: a crash, a
wrong-length result or a malformed grid is recorded against the task and the run
continues, because a harness that aborts on the first bad task cannot measure.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from arc.dataset import (
    MAX_DIM,
    MAX_SYMBOL,
    MIN_DIM,
    DatasetNotFoundError,
    Grid,
    Task,
    TaskFormatError,
    load_task,
)
from arc.dataset import task_ids as split_task_ids
from arc.solver import MAX_ATTEMPTS, Solver, trim_attempts

_WORKSPACE = Path(__file__).resolve().parent.parent

# Failing task ids quoted in `summary()`; the rest live in the JSON dump.
_SUMMARY_FAILURES = 10


class SolverOutputError(ValueError):
    """A solver returned something that cannot be scored."""


def grids_equal(a: object, b: object) -> bool:
    """True when two grids match exactly — dimensions and every cell.

    Takes `object` on purpose: an attempt of the wrong shape, or of no shape at
    all, is a miss to be counted, never an exception to be handled.
    """
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return False
    for row_a, row_b in zip(a, b, strict=True):
        if not isinstance(row_a, list) or not isinstance(row_b, list) or len(row_a) != len(row_b):
            return False
        if any(x != y for x, y in zip(row_a, row_b, strict=True)):
            return False
    return True


def _check_grid(grid: object, where: str) -> Grid:
    """Reject anything that is not a well-formed ARC grid."""
    if not isinstance(grid, list) or not grid:
        raise SolverOutputError(
            f"{where}: expected a non-empty list of rows, got {type(grid).__name__}"
        )

    width = None
    for r, row in enumerate(grid):
        if not isinstance(row, list) or not row:
            raise SolverOutputError(f"{where}: row {r} must be a non-empty list")
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise SolverOutputError(
                f"{where}: ragged grid — row {r} has {len(row)} cells, expected {width}"
            )
        for c, cell in enumerate(row):
            # bool is an int subclass; a True in a grid is always a bug.
            if isinstance(cell, bool) or not isinstance(cell, int):
                raise SolverOutputError(f"{where}: cell ({r},{c}) is {cell!r}, expected an int")
            if not 0 <= cell <= MAX_SYMBOL:
                raise SolverOutputError(
                    f"{where}: cell ({r},{c}) is {cell}, outside the 0-{MAX_SYMBOL} symbol range"
                )

    height, width = len(grid), width or 0
    if not (MIN_DIM <= height <= MAX_DIM and MIN_DIM <= width <= MAX_DIM):
        raise SolverOutputError(
            f"{where}: grid is {height}x{width}, outside the "
            f"{MIN_DIM}x{MIN_DIM}-{MAX_DIM}x{MAX_DIM} range"
        )
    return grid


@dataclass(frozen=True)
class TaskRecord:
    """How one solver fared on one task."""

    task_id: str
    solved: bool
    n_test: int
    n_correct: int
    attempts_used: tuple[int, ...]
    seconds: float
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "solved": self.solved,
            "n_test": self.n_test,
            "n_correct": self.n_correct,
            "attempts_used": list(self.attempts_used),
            "seconds": round(self.seconds, 6),
            "error": self.error,
        }


@dataclass(frozen=True)
class RunMeta:
    """Provenance for a run, so a reported number can be traced back."""

    solver: str
    split: str
    timestamp: str
    git_commit: str | None
    python_version: str
    n_tasks: int
    max_attempts: int = MAX_ATTEMPTS

    def to_dict(self) -> dict[str, Any]:
        return {
            "solver": self.solver,
            "split": self.split,
            "timestamp": self.timestamp,
            "git_commit": self.git_commit,
            "python_version": self.python_version,
            "n_tasks": self.n_tasks,
            "max_attempts": self.max_attempts,
        }


@dataclass(frozen=True)
class EvalResult:
    """Aggregate score for one run, plus every per-task record behind it."""

    meta: RunMeta
    records: tuple[TaskRecord, ...] = ()

    @property
    def solver(self) -> str:
        return self.meta.solver

    @property
    def split(self) -> str:
        return self.meta.split

    @property
    def total(self) -> int:
        return len(self.records)

    @property
    def solved(self) -> int:
        return sum(1 for r in self.records if r.solved)

    @property
    def accuracy(self) -> float:
        """Solved tasks over tasks evaluated; 0.0 for an empty run."""
        return self.solved / self.total if self.records else 0.0

    @property
    def total_seconds(self) -> float:
        return sum(r.seconds for r in self.records)

    @property
    def mean_seconds(self) -> float:
        return self.total_seconds / self.total if self.records else 0.0

    @property
    def n_errors(self) -> int:
        return sum(1 for r in self.records if r.error is not None)

    @property
    def failed_task_ids(self) -> tuple[str, ...]:
        return tuple(r.task_id for r in self.records if not r.solved)

    @property
    def error_task_ids(self) -> tuple[str, ...]:
        return tuple(r.task_id for r in self.records if r.error is not None)

    def summary(self) -> str:
        """Human-readable report, one fact per line."""
        pct = 100.0 * self.accuracy
        lines = [
            f"solver     {self.solver}",
            f"split      {self.split}",
            f"commit     {self.meta.git_commit or 'unknown'}",
            f"run        {self.meta.timestamp}",
            f"solved     {self.solved}/{self.total}  ({pct:.2f}%)",
            f"time       {self.total_seconds:.2f}s total, {self.mean_seconds:.3f}s/task",
            f"errors     {self.n_errors}",
        ]
        failed = self.failed_task_ids
        if failed:
            shown = ", ".join(failed[:_SUMMARY_FAILURES])
            more = len(failed) - _SUMMARY_FAILURES
            lines.append(f"failed     {shown}" + (f", ... (+{more} more)" if more > 0 else ""))
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "meta": self.meta.to_dict(),
            "solved": self.solved,
            "total": self.total,
            "accuracy": self.accuracy,
            "total_seconds": round(self.total_seconds, 6),
            "mean_seconds": round(self.mean_seconds, 6),
            "n_errors": self.n_errors,
            "records": [r.to_dict() for r in self.records],
        }

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)

    def dump(self, path: str | os.PathLike[str], *, indent: int = 2) -> Path:
        """Write the full result (records included) to `path`."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_json(indent=indent) + "\n", encoding="utf-8")
        return out


def git_commit(cwd: str | os.PathLike[str] | None = None) -> str | None:
    """Short HEAD hash for provenance, or None outside a usable git checkout."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=os.fspath(cwd) if cwd is not None else _WORKSPACE,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = proc.stdout.strip()
    return commit if proc.returncode == 0 and commit else None


def solver_name(solver: Solver) -> str:
    """Registered name of `solver`, falling back to its class name."""
    name = getattr(solver, "name", None)
    return str(name) if name else type(solver).__name__


def _score_task(solver: Solver, task: Task) -> tuple[int, tuple[int, ...]]:
    """Return (correct test inputs, attempts scored per test input).

    Raises SolverOutputError when the solver's shape does not fit the task.
    """
    raw = solver.solve(task)
    if not isinstance(raw, (list, tuple)):
        raise SolverOutputError(
            f"solve() returned {type(raw).__name__}, expected a list of attempt lists"
        )
    if len(raw) != len(task.test):
        raise SolverOutputError(
            f"solve() returned {len(raw)} attempt list(s) for {len(task.test)} test input(s)"
        )

    n_correct = 0
    used: list[int] = []
    for i, (attempts, pair) in enumerate(zip(raw, task.test, strict=True)):
        if pair.output is None:
            raise SolverOutputError(f"test[{i}] has no expected output — cannot be scored")
        if not isinstance(attempts, (list, tuple)):
            raise SolverOutputError(
                f"test[{i}]: expected a list of attempt grids, got {type(attempts).__name__}"
            )
        try:
            # Trim first: anything past the 2-attempt limit is never looked at.
            trimmed = trim_attempts(list(attempts), MAX_ATTEMPTS)
        except Exception as exc:  # a comparison inside the dedupe can itself blow up
            raise SolverOutputError(f"test[{i}]: attempts could not be trimmed — {exc!r}") from exc
        for j, grid in enumerate(trimmed):
            _check_grid(grid, f"test[{i}].attempt[{j}]")
        used.append(len(trimmed))
        if any(grids_equal(grid, pair.output) for grid in trimmed):
            n_correct += 1
    return n_correct, tuple(used)


def evaluate_task(solver: Solver, task: Task) -> TaskRecord:
    """Score one task under the official rules; never raises for solver faults."""
    started = time.perf_counter()
    n_test = len(task.test)
    try:
        n_correct, used = _score_task(solver, task)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        return TaskRecord(
            task_id=task.task_id,
            solved=False,
            n_test=n_test,
            n_correct=0,
            attempts_used=(),
            seconds=elapsed,
            error=f"{type(exc).__name__}: {exc}",
        )
    elapsed = time.perf_counter() - started
    return TaskRecord(
        task_id=task.task_id,
        solved=n_correct == n_test and n_test > 0,
        n_test=n_test,
        n_correct=n_correct,
        attempts_used=used,
        seconds=elapsed,
    )


def _select_ids(split: str, task_ids: Sequence[str] | None, limit: int | None) -> list[str]:
    ids = list(task_ids) if task_ids is not None else list(split_task_ids(split))
    if limit is not None:
        if limit < 0:
            raise ValueError(f"limit must be >= 0, got {limit}")
        ids = ids[:limit]
    return ids


def evaluate(
    solver: Solver,
    split: str = "evaluation",
    *,
    task_ids: Sequence[str] | None = None,
    limit: int | None = None,
    on_task: Callable[[TaskRecord], None] | None = None,
) -> EvalResult:
    """Run `solver` over `split` and score it under the official rules.

    `task_ids` restricts the run to those ids (in the order given), `limit` to
    the first N, and `on_task` is called with each record as it lands so a caller
    can show progress. A missing dataset still raises — that is an environment
    problem, not a measurement — but nothing a solver does aborts the run.
    """
    ids = _select_ids(split, task_ids, limit)
    records: list[TaskRecord] = []

    for task_id in ids:
        try:
            task = load_task(task_id, split)
        except DatasetNotFoundError:
            raise
        except TaskFormatError as exc:
            record = TaskRecord(
                task_id=task_id,
                solved=False,
                n_test=0,
                n_correct=0,
                attempts_used=(),
                seconds=0.0,
                error=f"{type(exc).__name__}: {exc}",
            )
        else:
            record = evaluate_task(solver, task)
        records.append(record)
        if on_task is not None:
            on_task(record)

    meta = RunMeta(
        solver=solver_name(solver),
        split=split,
        timestamp=datetime.now(UTC).isoformat(timespec="seconds"),
        git_commit=git_commit(),
        python_version=platform.python_version(),
        n_tasks=len(records),
    )
    return EvalResult(meta=meta, records=tuple(records))
