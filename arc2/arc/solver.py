"""Solver protocol and registry for ARC-AGI-2.

A solver maps a Task to candidate output grids: one list of attempts per test
input, at most `MAX_ATTEMPTS` grids each. The competition allows 2 attempts per
test input, and a task counts as solved only when *every* test input is matched
exactly — dimensions included — by one of its attempts.

Returning fewer attempts (or none) is legal: a solver that knows it has no idea
should abstain rather than pad with guesses, so that per-solver coverage stays
readable in the evaluation report.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

from arc.dataset import Grid, Task

# Competition rule: 2 trials per test input, for humans and machines alike.
MAX_ATTEMPTS = 2

# Candidate outputs for a single test input, best guess first.
Attempts = list[Grid]

SolverFactory = Callable[[], "Solver"]


@runtime_checkable
class Solver(Protocol):
    """Anything that proposes output grids for a task's test inputs."""

    name: str

    def solve(self, task: Task) -> list[Attempts]:
        """Return one Attempts list per entry in `task.test`, in order."""
        ...


_REGISTRY: dict[str, SolverFactory] = {}


def register(name: str) -> Callable[[SolverFactory], SolverFactory]:
    """Register a zero-argument factory under `name`.

    Used as a decorator on a Solver class or a function returning one:

        @register("identity")
        class IdentitySolver:
            name = "identity"
            def solve(self, task): ...
    """

    def wrap(factory: SolverFactory) -> SolverFactory:
        if name in _REGISTRY:
            raise ValueError(f"solver {name!r} is already registered")
        _REGISTRY[name] = factory
        return factory

    return wrap


def _load_builtins() -> None:
    """Import the bundled solver package so its registrations run."""
    try:
        import arc.solvers  # noqa: F401
    except ModuleNotFoundError:
        # The solver package is optional; an empty registry is still valid.
        pass


def available_solvers() -> tuple[str, ...]:
    """Names of every registered solver, sorted."""
    _load_builtins()
    return tuple(sorted(_REGISTRY))


def get_solver(name: str) -> Solver:
    """Build the solver registered under `name`."""
    _load_builtins()
    if name not in _REGISTRY:
        known = ", ".join(available_solvers()) or "(none registered)"
        raise KeyError(f"unknown solver {name!r}; available: {known}")
    return _REGISTRY[name]()


def trim_attempts(attempts: list[Grid], limit: int = MAX_ATTEMPTS) -> Attempts:
    """Drop duplicates and anything past the attempt limit, preserving order.

    Solvers routinely produce the same grid by two different routes; a repeated
    guess wastes a trial, so the harness treats duplicates as a single attempt.
    """
    seen: list[Grid] = []
    for grid in attempts:
        if grid not in seen:
            seen.append(grid)
        if len(seen) == limit:
            break
    return seen
