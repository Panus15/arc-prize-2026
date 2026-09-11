"""Tests for the rule-based baseline solvers.

The contract that matters most here is *fit then abstain*: a rule may answer
only when it reproduces every demonstration output. A rule that guesses instead
of abstaining still scores near zero, but it destroys the precision figure that
makes the baselines worth reporting — so the protocol invariants below are
checked against every registered solver, not just the ones a test names.
"""

from __future__ import annotations

import pytest

from arc.dataset import parse_task
from arc.solver import MAX_ATTEMPTS, available_solvers, get_solver

ALL_SOLVERS = available_solvers()


def make_task(train: list[tuple[list, list]], test: list[tuple[list, list]]):
    """Build a Task from (input, output) grid pairs."""
    payload = {
        "train": [{"input": i, "output": o} for i, o in train],
        "test": [{"input": i, "output": o} for i, o in test],
    }
    return parse_task(payload, task_id="synthetic")


# A task with no learnable structure: outputs are unrelated to inputs.
NOISE = make_task(
    train=[
        ([[1, 2], [3, 4]], [[7, 0, 5], [2, 9, 1], [4, 4, 8]]),
        ([[5, 5], [6, 7]], [[3, 1, 2], [8, 0, 6], [9, 9, 7]]),
    ],
    test=[([[8, 1], [2, 3]], [[1, 1, 1], [2, 2, 2], [3, 3, 3]])],
)


def test_registry_is_populated():
    assert ALL_SOLVERS, "no solvers registered — arc.solvers failed to import"


# --- protocol invariants, enforced on every registered solver ---------------


@pytest.mark.parametrize("name", ALL_SOLVERS)
def test_returns_one_attempts_list_per_test_input(name):
    task = make_task(
        train=[([[1]], [[1]]), ([[2]], [[2]])],
        test=[([[3]], [[3]]), ([[4]], [[4]])],
    )
    out = get_solver(name).solve(task)
    assert len(out) == len(task.test)


@pytest.mark.parametrize("name", ALL_SOLVERS)
def test_never_exceeds_the_attempt_limit(name):
    for task in (NOISE, make_task([([[1, 1]], [[1, 1]])], [([[2, 2]], [[2, 2]])])):
        for attempts in get_solver(name).solve(task):
            assert len(attempts) <= MAX_ATTEMPTS


@pytest.mark.parametrize("name", ALL_SOLVERS)
def test_abstains_when_the_rule_cannot_explain_the_demonstrations(name):
    """The core discipline: no fit, no answer."""
    out = get_solver(name).solve(NOISE)
    assert len(out) == len(NOISE.test)
    assert all(attempts == [] for attempts in out), (
        f"{name} guessed on a task it cannot explain; it must abstain instead"
    )


@pytest.mark.parametrize("name", ALL_SOLVERS)
def test_solver_exposes_its_registered_name(name):
    assert get_solver(name).name == name


# --- individual rules solve what they are meant to solve --------------------


def solved_by(name: str, task) -> bool:
    """True when the solver's attempts contain the expected output for every test input."""
    out = get_solver(name).solve(task)
    if len(out) != len(task.test):
        return False
    return all(
        any(grid == pair.output for grid in attempts)
        for attempts, pair in zip(out, task.test, strict=True)
    )


def test_identity_solves_an_identity_task():
    task = make_task(
        train=[([[1, 2], [3, 4]], [[1, 2], [3, 4]]), ([[5, 0]], [[5, 0]])],
        test=[([[7, 8], [9, 1]], [[7, 8], [9, 1]])],
    )
    assert solved_by("identity", task)


def test_geometry_solves_a_rotation_task():
    # 180-degree rotation, consistent across both demonstrations.
    task = make_task(
        train=[([[1, 2], [3, 4]], [[4, 3], [2, 1]]), ([[5, 6], [7, 8]], [[8, 7], [6, 5]])],
        test=[([[1, 0], [0, 2]], [[2, 0], [0, 1]])],
    )
    assert solved_by("geometry", task)


def test_colour_map_solves_a_recolour_task():
    task = make_task(
        train=[([[1, 2], [2, 1]], [[3, 4], [4, 3]]), ([[1, 1], [2, 2]], [[3, 3], [4, 4]])],
        test=[([[2, 1], [1, 2]], [[4, 3], [3, 4]])],
    )
    assert solved_by("colour_map", task)


def test_upscale_solves_a_block_expansion_task():
    task = make_task(
        train=[
            ([[1, 2]], [[1, 1, 2, 2], [1, 1, 2, 2]]),
            ([[3, 0]], [[3, 3, 0, 0], [3, 3, 0, 0]]),
        ],
        test=[([[5, 6]], [[5, 5, 6, 6], [5, 5, 6, 6]])],
    )
    assert solved_by("upscale", task)


def test_composite_inherits_what_its_parts_can_solve():
    task = make_task(
        train=[([[1, 2], [3, 4]], [[4, 3], [2, 1]]), ([[5, 6], [7, 8]], [[8, 7], [6, 5]])],
        test=[([[1, 0], [0, 2]], [[2, 0], [0, 1]])],
    )
    assert solved_by("composite", task)


def test_composite_abstains_on_noise():
    assert all(attempts == [] for attempts in get_solver("composite").solve(NOISE))
