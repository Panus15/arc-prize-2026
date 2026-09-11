"""Tests for the official-rules scoring harness.

Everything here builds Tasks from inline payloads and drives `evaluate` against
an in-memory corpus, so the unit tests need no ARC-AGI-2 checkout. The few tests
that touch the real corpus are marked and skip when it is absent.
"""

from __future__ import annotations

import json

import pytest

from arc import evaluate as ev
from arc.dataset import DatasetNotFoundError, Grid, Task, TaskFormatError, parse_task, task_ids
from arc.evaluate import EvalResult, evaluate, evaluate_task, grids_equal
from arc.solver import MAX_ATTEMPTS

TRAIN = [{"input": [[1, 2], [3, 4]], "output": [[4, 3], [2, 1]]}]
ANSWER: Grid = [[1, 2], [3, 4]]


def make_task(task_id: str, *outputs: Grid) -> Task:
    """A task whose test inputs each expect the matching grid in `outputs`."""
    payload = {
        "train": TRAIN,
        "test": [{"input": [[0]], "output": out} for out in (outputs or (ANSWER,))],
    }
    return parse_task(payload, task_id=task_id, split="training")


class FixedSolver:
    """Returns the same attempt list for every test input."""

    def __init__(self, attempts: list[Grid], name: str = "fixed"):
        self.name = name
        self._attempts = attempts

    def solve(self, task: Task) -> list[list[Grid]]:
        return [list(self._attempts) for _ in task.test]


class ScriptedSolver:
    """Returns whatever `script` maps the task id to — including junk."""

    name = "scripted"

    def __init__(self, script: dict[str, object]):
        self._script = script

    def solve(self, task: Task):
        value = self._script[task.task_id]
        if isinstance(value, Exception):
            raise value
        return value


def install_corpus(monkeypatch, tasks: list[Task]) -> None:
    """Swap the dataset lookups for an in-memory corpus."""
    by_id = {t.task_id: t for t in tasks}

    def fake_task_ids(split: str) -> tuple[str, ...]:
        return tuple(by_id)

    def fake_load_task(task_id: str, split: str = "training") -> Task:
        if task_id not in by_id:
            raise DatasetNotFoundError(f"no task {task_id!r}")
        return by_id[task_id]

    monkeypatch.setattr(ev, "split_task_ids", fake_task_ids)
    monkeypatch.setattr(ev, "load_task", fake_load_task)


def _dataset_available() -> bool:
    try:
        task_ids("training")
    except DatasetNotFoundError:
        return False
    return True


needs_dataset = pytest.mark.skipif(
    not _dataset_available(),
    reason="ARC-AGI-2 checkout missing — run ./setup.sh (or setup.bat) first",
)


# --- exact matching --------------------------------------------------------


def test_exact_match_scores():
    record = evaluate_task(FixedSolver([ANSWER]), make_task("hit"))
    assert record.solved
    assert (record.n_correct, record.n_test) == (1, 1)
    assert record.attempts_used == (1,)
    assert record.error is None
    assert record.seconds >= 0.0


def test_one_cell_off_fails():
    record = evaluate_task(FixedSolver([[[1, 2], [3, 5]]]), make_task("near"))
    assert not record.solved
    assert record.n_correct == 0
    assert record.error is None


@pytest.mark.parametrize(
    "attempt",
    [
        [[1, 2, 3, 4]],  # right cells, flattened
        [[1, 2]],  # right cells, missing a row
        [[1, 2], [3, 4], [0, 0]],  # right cells plus padding
        [[1, 2, 0], [3, 4, 0]],  # right cells plus a column
    ],
    ids=["flat", "short", "tall", "wide"],
)
def test_right_cells_wrong_dimensions_fail(attempt):
    record = evaluate_task(FixedSolver([attempt]), make_task("dims"))
    assert not record.solved
    assert record.error is None


def test_grids_equal_is_exact():
    assert grids_equal([[1, 2], [3, 4]], [[1, 2], [3, 4]])
    assert not grids_equal([[1, 2], [3, 4]], [[1, 2], [3, 5]])
    assert not grids_equal([[1, 2]], [[1], [2]])
    assert not grids_equal([[1]], "nope")


# --- the two-attempt rule --------------------------------------------------


def test_second_attempt_counts():
    solver = FixedSolver([[[9, 9], [9, 9]], ANSWER])
    record = evaluate_task(solver, make_task("second"))
    assert record.solved
    assert record.attempts_used == (MAX_ATTEMPTS,)


def test_third_attempt_does_not_count():
    solver = FixedSolver([[[9, 9], [9, 9]], [[8, 8], [8, 8]], ANSWER])
    record = evaluate_task(solver, make_task("third"))
    assert not record.solved
    assert record.attempts_used == (MAX_ATTEMPTS,)


def test_duplicate_guess_does_not_burn_both_trials():
    # trim_attempts dedupes, so a repeated first guess leaves the second trial free.
    solver = FixedSolver([[[9, 9], [9, 9]], [[9, 9], [9, 9]], ANSWER])
    assert evaluate_task(solver, make_task("dupe")).solved


# --- multi test input tasks ------------------------------------------------


def test_all_test_inputs_must_be_correct():
    task = make_task("multi", ANSWER, [[5, 5], [5, 5]])
    record = evaluate_task(FixedSolver([ANSWER]), task)
    assert record.n_test == 2
    assert record.n_correct == 1
    assert not record.solved
    assert record.error is None


def test_every_test_input_correct_scores():
    task = make_task("multi-ok", ANSWER, ANSWER)
    record = evaluate_task(FixedSolver([ANSWER]), task)
    assert record.solved and record.n_correct == 2


# --- abstaining and faults -------------------------------------------------


def test_abstaining_is_unsolved_but_not_an_error():
    record = evaluate_task(FixedSolver([]), make_task("abstain"))
    assert not record.solved
    assert record.error is None
    assert record.attempts_used == (0,)


def test_raising_solver_is_recorded_as_an_error():
    solver = ScriptedSolver({"boom": RuntimeError("kaboom")})
    record = evaluate_task(solver, make_task("boom"))
    assert not record.solved
    assert record.error is not None
    assert "RuntimeError" in record.error and "kaboom" in record.error


@pytest.mark.parametrize(
    ("returned", "match"),
    [
        ([], "0 attempt list"),  # too few attempt lists
        ([[ANSWER], [ANSWER]], "2 attempt list"),  # too many attempt lists
        (None, "expected a list of attempt lists"),  # not a list at all
        ([None], "expected a list of attempt grids"),  # attempts are not a list
        ([ANSWER], "row 0 must be a non-empty list"),  # forgot the outer list
        ([[[[1, 2], [3]]]], "ragged"),  # malformed grid
        ([[[[1, 2], [3, 99]]]], "symbol range"),
        ([[[]]], "non-empty list of rows"),
        ([[[[1, 2], "x"]]], "row 1 must be a non-empty list"),
    ],
    ids=[
        "short",
        "long",
        "not-a-list",
        "attempts-not-a-list",
        "unwrapped",
        "ragged",
        "symbol",
        "empty",
        "bad-row",
    ],
)
def test_malformed_solver_output_is_an_error(returned, match):
    record = evaluate_task(ScriptedSolver({"bad": returned}), make_task("bad"))
    assert not record.solved
    assert record.error is not None and match in record.error


def test_missing_expected_output_is_an_error():
    payload = {"train": TRAIN, "test": [{"input": [[0]]}]}
    task = parse_task(payload, task_id="held-out", split="training")
    record = evaluate_task(FixedSolver([ANSWER]), task)
    assert record.error is not None and "cannot be scored" in record.error


# --- run-level aggregation -------------------------------------------------


def test_run_continues_past_a_raising_solver(monkeypatch):
    install_corpus(monkeypatch, [make_task("a"), make_task("b"), make_task("c")])
    solver = ScriptedSolver({"a": [[ANSWER]], "b": ValueError("nope"), "c": [[ANSWER]]})
    result = evaluate(solver, "training")

    assert result.total == 3
    assert result.solved == 2
    assert result.n_errors == 1
    assert result.error_task_ids == ("b",)
    assert result.failed_task_ids == ("b",)


def test_unloadable_task_is_recorded_not_raised(monkeypatch):
    good = make_task("a")

    def fake_load_task(task_id: str, split: str = "training") -> Task:
        if task_id == "broken":
            raise TaskFormatError("broken: grid is ragged")
        return good

    monkeypatch.setattr(ev, "split_task_ids", lambda split: ("a", "broken"))
    monkeypatch.setattr(ev, "load_task", fake_load_task)

    result = evaluate(FixedSolver([ANSWER]), "training")
    assert result.solved == 1 and result.total == 2
    assert result.error_task_ids == ("broken",)


def test_missing_dataset_still_raises(monkeypatch):
    # An absent corpus is an environment fault, not a measurement to report.
    def boom(task_id: str, split: str = "training") -> Task:
        raise DatasetNotFoundError("no checkout")

    monkeypatch.setattr(ev, "load_task", boom)
    with pytest.raises(DatasetNotFoundError):
        evaluate(FixedSolver([ANSWER]), "training", task_ids=["a"])


def test_accuracy_arithmetic(monkeypatch):
    tasks = [make_task(f"t{i}") for i in range(4)]
    install_corpus(monkeypatch, tasks)
    # Solves t0 and t1 only.
    script = {"t0": [[ANSWER]], "t1": [[ANSWER]], "t2": [[]], "t3": [[]]}
    result = evaluate(ScriptedSolver(script), "training")

    assert (result.solved, result.total) == (2, 4)
    assert result.accuracy == pytest.approx(0.5)
    assert result.total_seconds == pytest.approx(sum(r.seconds for r in result.records))
    assert result.mean_seconds == pytest.approx(result.total_seconds / 4)


def test_empty_run_has_zero_accuracy(monkeypatch):
    install_corpus(monkeypatch, [])
    result = evaluate(FixedSolver([ANSWER]), "training")
    assert (result.total, result.solved, result.accuracy) == (0, 0, 0.0)
    assert result.mean_seconds == 0.0
    assert "0/0" in result.summary()


def test_limit_and_task_id_selection(monkeypatch):
    install_corpus(monkeypatch, [make_task(f"t{i}") for i in range(5)])
    solver = FixedSolver([ANSWER])

    assert [r.task_id for r in evaluate(solver, "training", limit=2).records] == ["t0", "t1"]
    picked = evaluate(solver, "training", task_ids=["t3", "t1"]).records
    assert [r.task_id for r in picked] == ["t3", "t1"]
    assert evaluate(solver, "training", limit=0).total == 0


def test_on_task_callback_sees_every_record(monkeypatch):
    install_corpus(monkeypatch, [make_task("a"), make_task("b")])
    seen: list[str] = []
    result = evaluate(FixedSolver([ANSWER]), "training", on_task=lambda r: seen.append(r.task_id))
    assert seen == ["a", "b"] == [r.task_id for r in result.records]


# --- provenance and serialisation ------------------------------------------


def test_result_carries_run_metadata(monkeypatch):
    install_corpus(monkeypatch, [make_task("a")])
    result = evaluate(FixedSolver([ANSWER], name="fixed"), "training")

    meta = result.meta
    assert meta.solver == "fixed"
    assert meta.split == "training"
    assert meta.n_tasks == 1
    assert meta.max_attempts == MAX_ATTEMPTS
    assert meta.timestamp.endswith("+00:00")
    assert meta.python_version.count(".") == 2
    assert meta.git_commit is None or meta.git_commit.strip() == meta.git_commit


def test_git_commit_tolerates_a_non_repository(tmp_path):
    assert ev.git_commit(tmp_path) is None


def test_to_json_round_trips(monkeypatch):
    install_corpus(monkeypatch, [make_task("a"), make_task("b", ANSWER, [[7]])])
    result = evaluate(ScriptedSolver({"a": [[ANSWER]], "b": [[ANSWER], []]}), "training")
    payload = json.loads(result.to_json())

    assert payload["solved"] == 1 and payload["total"] == 2
    assert payload["accuracy"] == pytest.approx(0.5)
    assert [r["task_id"] for r in payload["records"]] == ["a", "b"]
    assert payload["records"][1]["n_correct"] == 1
    assert payload["meta"]["solver"] == "scripted"


def test_dump_writes_the_full_result(tmp_path, monkeypatch):
    install_corpus(monkeypatch, [make_task("a")])
    result = evaluate(FixedSolver([ANSWER]), "training")
    out = result.dump(tmp_path / "runs" / "result.json")

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["records"][0]["solved"] is True
    assert payload["meta"]["split"] == "training"


def test_summary_is_readable(monkeypatch):
    install_corpus(monkeypatch, [make_task("a"), make_task("b", [[7]])])
    text = evaluate(FixedSolver([ANSWER]), "training").summary()

    assert "solved     1/2  (50.00%)" in text
    assert "s/task" in text
    assert "errors     0" in text
    assert "failed     b" in text


def test_summary_truncates_long_failure_lists(monkeypatch):
    install_corpus(monkeypatch, [make_task(f"t{i}", [[7]]) for i in range(15)])
    text = evaluate(FixedSolver([ANSWER]), "training").summary()
    assert "(+5 more)" in text


def test_eval_result_is_constructible_without_records():
    meta = ev.RunMeta(
        solver="none",
        split="training",
        timestamp="1970-01-01T00:00:00+00:00",
        git_commit=None,
        python_version="3.11.0",
        n_tasks=0,
    )
    assert EvalResult(meta=meta).accuracy == 0.0


# --- CLI -------------------------------------------------------------------


def test_cli_rejects_unknown_solver(capsys):
    from arc.__main__ import main

    code = main(["eval", "--solver", "definitely-not-a-solver"])
    err = capsys.readouterr().err
    assert code != 0
    assert "definitely-not-a-solver" in err or "no solvers are registered" in err


# --- the real corpus -------------------------------------------------------


@needs_dataset
def test_scores_real_tasks():
    ids = task_ids("training")[:3]
    result = evaluate(FixedSolver([ANSWER]), "training", task_ids=list(ids))
    assert result.total == 3
    assert result.n_errors == 0
    assert all(r.n_test >= 1 for r in result.records)
    assert 0.0 <= result.accuracy <= 1.0
