"""Command line entry point: `python -m arc <command>`."""

from __future__ import annotations

import argparse
import statistics
import sys
from collections import Counter
from collections.abc import Callable

from arc.dataset import (
    EXPECTED_COUNTS,
    SPLITS,
    DatasetNotFoundError,
    TaskFormatError,
    data_root,
    grid_shapes,
    iter_split,
    load_task,
    task_ids,
)
from arc.evaluate import TaskRecord, evaluate
from arc.render import render_task
from arc.solver import available_solvers, get_solver


def _verify(args: argparse.Namespace) -> int:
    splits = [args.split] if args.split else list(SPLITS)
    print(f"dataset: {data_root()}")
    failures: list[str] = []

    for split in splits:
        ids = task_ids(split)
        expected = EXPECTED_COUNTS.get(split)
        count_note = ""
        if expected is not None and len(ids) != expected:
            count_note = f"  [!] expected {expected}"
            failures.append(f"{split}: found {len(ids)} tasks, expected {expected}")

        # Load each task individually so one malformed file does not hide the rest.
        passed = 0
        for task_id in ids:
            try:
                task = load_task(task_id, split)
                # The public splits always ship test outputs; a missing one means
                # a truncated or wrong checkout rather than a held-out set.
                for i, pair in enumerate(task.test):
                    if pair.output is None:
                        raise TaskFormatError(f"{task_id}: test[{i}] has no 'output'")
            except TaskFormatError as exc:
                failures.append(str(exc))
                continue
            passed += 1

        print(f"  {split:<11} {passed:>5}/{len(ids)} tasks validated{count_note}")

    if failures:
        print(f"\nFAILED — {len(failures)} problem(s):", file=sys.stderr)
        for line in failures[:20]:
            print(f"  - {line}", file=sys.stderr)
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more", file=sys.stderr)
        return 1

    print("\nOK — every task parses and matches the ARC grid spec.")
    return 0


def _show(args: argparse.Namespace) -> int:
    colour = False if args.no_color else None
    task = load_task(args.task_id, args.split)
    print(render_task(task, colour=colour))
    return 0


def _stats(args: argparse.Namespace) -> int:
    splits = [args.split] if args.split else list(SPLITS)
    for split in splits:
        tasks = list(iter_split(split))
        shapes = grid_shapes(tasks)
        cells = [h * w for h, w in shapes]
        train_pairs = Counter(len(t.train) for t in tasks)
        test_pairs = Counter(len(t.test) for t in tasks)

        tallest, widest = max(s[0] for s in shapes), max(s[1] for s in shapes)
        print(f"[{split}] {len(tasks)} tasks, {len(shapes)} grids")
        print(
            f"  grid cells  min {min(cells)}  median {int(statistics.median(cells))}"
            f"  max {max(cells)}"
        )
        print(f"  max dims    {tallest} rows x {widest} cols")
        print(f"  train pairs {dict(sorted(train_pairs.items()))}")
        print(f"  test pairs  {dict(sorted(test_pairs.items()))}")
    return 0


def _progress_printer() -> Callable[[TaskRecord], None]:
    """Per-task progress on stderr, so `--json` on stdout stays pipeable."""
    seen = solved = 0

    def report(record: TaskRecord) -> None:
        nonlocal seen, solved
        seen += 1
        solved += int(record.solved)
        mark = "ok " if record.solved else ("ERR" if record.error else " . ")
        print(
            f"[{seen:>5}] {mark} {record.task_id}  {record.seconds:6.3f}s  {solved} solved",
            file=sys.stderr,
        )

    return report


def _eval(args: argparse.Namespace) -> int:
    known = available_solvers()
    if not known:
        print(
            "error: no solvers are registered — add one under arc/solvers/ with "
            "@arc.solver.register(name), then re-run.",
            file=sys.stderr,
        )
        return 2
    try:
        solver = get_solver(args.solver)
    except KeyError:
        print(f"error: unknown solver {args.solver!r}", file=sys.stderr)
        print(f"available solvers: {', '.join(known)}", file=sys.stderr)
        return 2

    if args.limit is not None and args.limit < 0:
        print(f"error: --limit must be >= 0, got {args.limit}", file=sys.stderr)
        return 2

    ids = None
    if args.task_ids:
        ids = [t.strip() for t in args.task_ids.split(",") if t.strip()]
        if not ids:
            print("error: --task-ids listed no task ids", file=sys.stderr)
            return 2

    result = evaluate(
        solver,
        args.split,
        task_ids=ids,
        limit=args.limit,
        on_task=None if args.quiet else _progress_printer(),
    )
    print(result.summary())
    if args.json:
        print(f"\nwrote {result.dump(args.json)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="arc", description="ARC-AGI-2 dataset tools")
    sub = parser.add_subparsers(dest="command", required=True)

    p_verify = sub.add_parser("verify", help="validate every task file against the grid spec")
    p_verify.add_argument("--split", choices=SPLITS, help="only this split (default: both)")
    p_verify.set_defaults(func=_verify)

    p_show = sub.add_parser("show", help="render one task in the terminal")
    p_show.add_argument("task_id", help="task id, e.g. 007bbfb7")
    p_show.add_argument("--split", choices=SPLITS, default="training")
    p_show.add_argument("--no-color", action="store_true", help="print symbols instead of colour")
    p_show.set_defaults(func=_show)

    p_stats = sub.add_parser("stats", help="summarise grid sizes and pair counts")
    p_stats.add_argument("--split", choices=SPLITS, help="only this split (default: both)")
    p_stats.set_defaults(func=_stats)

    p_eval = sub.add_parser("eval", help="score a solver under the official 2-attempt rules")
    p_eval.add_argument("--solver", required=True, help="registered solver name")
    p_eval.add_argument("--split", choices=SPLITS, default="evaluation")
    p_eval.add_argument("--limit", type=int, metavar="N", help="only the first N tasks")
    p_eval.add_argument("--task-ids", metavar="A,B,C", help="only these task ids, comma separated")
    p_eval.add_argument("--json", metavar="OUT", help="write the full result, records included")
    p_eval.add_argument("--quiet", action="store_true", help="no per-task progress on stderr")
    p_eval.set_defaults(func=_eval)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (DatasetNotFoundError, TaskFormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
