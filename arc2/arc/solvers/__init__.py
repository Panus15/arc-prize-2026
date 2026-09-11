"""Rule-based baseline solvers.

Every rule here follows the same contract: fit its parameters on `task.train`,
verify the fitted rule reproduces *every* demonstration output exactly, and
abstain otherwise. That keeps precision high and makes "how many tasks does
this rule explain" a number worth quoting. See `docs/baselines.md` for the
measured coverage of each.

Importing this package registers every solver, which is what
`arc.solver._load_builtins()` relies on.
"""

from __future__ import annotations

from arc.solvers import (  # noqa: F401 — imported for their registration side effects
    basic,
    composite,
    cropping,
    degenerate,
    geometry,
    panels,
    scaling,
    symmetry,
)
from arc.solvers.base import RuleSolver, Transform, attempts_for, explains_train
from arc.solvers.composite import RULE_ORDER, CompositeSolver

__all__ = [
    "RULE_ORDER",
    "CompositeSolver",
    "RuleSolver",
    "Transform",
    "attempts_for",
    "explains_train",
]
