"""Tests for the ARC-AGI-2 loader.

Schema tests run on inline payloads and need no checkout. Corpus tests are
skipped when the dataset has not been fetched yet.
"""

from __future__ import annotations

import json

import pytest

from arc.dataset import (
    EXPECTED_COUNTS,
    SPLITS,
    DatasetNotFoundError,
    TaskFormatError,
    load_task,
    load_task_file,
    parse_task,
    task_ids,
)
from arc.render import render_grid, render_task

MINIMAL = {
    "train": [{"input": [[1, 2], [3, 4]], "output": [[4, 3], [2, 1]]}],
    "test": [{"input": [[0]], "output": [[9]]}],
}


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


# --- schema handling -------------------------------------------------------


def test_parses_minimal_task():
    task = parse_task(MINIMAL, task_id="demo", split="training")
    assert task.task_id == "demo"
    assert len(task.train) == 1 and len(task.test) == 1
    assert task.train[0].input_shape == (2, 2)
    assert task.test[0].output == [[9]]
    assert len(task.pairs) == 2


def test_test_output_may_be_held_out():
    payload = {"train": MINIMAL["train"], "test": [{"input": [[0]]}]}
    task = parse_task(payload, task_id="held-out")
    assert task.test[0].output is None
    assert task.test[0].output_shape is None


def test_train_output_is_required():
    payload = {"train": [{"input": [[0]]}], "test": MINIMAL["test"]}
    with pytest.raises(TaskFormatError, match="missing 'output'"):
        parse_task(payload, task_id="bad")


@pytest.mark.parametrize(
    ("grid", "match"),
    [
        ([[1, 2], [3]], "ragged"),
        ([[10]], "symbol range"),
        ([[-1]], "symbol range"),
        ([[True]], "expected an int"),
        ([], "non-empty"),
        ([[1] * 31], "outside the"),
    ],
)
def test_rejects_malformed_grids(grid, match):
    payload = {"train": [{"input": grid, "output": [[0]]}], "test": MINIMAL["test"]}
    with pytest.raises(TaskFormatError, match=match):
        parse_task(payload, task_id="bad")


def test_rejects_missing_sections():
    with pytest.raises(TaskFormatError, match="missing 'test'"):
        parse_task({"train": MINIMAL["train"]}, task_id="bad")


def test_reports_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(TaskFormatError, match="invalid JSON"):
        load_task_file(path)


def test_load_task_file_round_trip(tmp_path):
    path = tmp_path / "abc123.json"
    path.write_text(json.dumps(MINIMAL), encoding="utf-8")
    assert load_task_file(path).task_id == "abc123"


# --- rendering -------------------------------------------------------------


def test_render_grid_without_colour_shows_symbols():
    assert render_grid([[1, 2], [3, 4]], colour=False) == "1 2 \n3 4 "


def test_render_task_labels_pairs():
    text = render_task(parse_task(MINIMAL, task_id="demo"), colour=False)
    assert "task demo" in text
    assert "train 0" in text and "test 0" in text
    assert "2x2 -> 2x2" in text


# --- the real corpus -------------------------------------------------------


@needs_dataset
@pytest.mark.parametrize("split", SPLITS)
def test_split_has_published_task_count(split):
    assert len(task_ids(split)) == EXPECTED_COUNTS[split]


@needs_dataset
@pytest.mark.parametrize("split", SPLITS)
def test_every_task_parses(split):
    for task_id in task_ids(split):
        task = load_task(task_id, split)
        assert task.train, f"{task_id} has no demonstration pairs"
        assert task.test, f"{task_id} has no test pairs"
        # Public splits ship the answers; held-out formats are handled elsewhere.
        assert all(p.output is not None for p in task.test), f"{task_id} is missing a test output"


@needs_dataset
def test_missing_task_id_is_reported():
    with pytest.raises(DatasetNotFoundError, match="no task"):
        load_task("does-not-exist", "training")
