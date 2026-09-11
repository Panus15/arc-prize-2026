"""Run every rule, keep the two best-supported answers.

Ordering is by how much evidence a fit represents, not by how often the rule
fires. A rule like `identity` or `colour_map` constrains every cell of every
demonstration, so a fit is hard to come by accidentally; `constant_output` only
says the demonstrations happen to agree, and `shape_fill` says almost nothing.
When several rules fit and disagree, the answer from the most constrained rule
goes first, and the degenerate ones fill the second attempt at best.
"""

from __future__ import annotations

from arc.dataset import Task
from arc.solver import Attempts, register, trim_attempts
from arc.solvers.base import RuleSolver
from arc.solvers.basic import ColourMapSolver, ConstantOutputSolver, IdentitySolver
from arc.solvers.cropping import CropSolver
from arc.solvers.degenerate import ShapeFillSolver
from arc.solvers.geometry import GeometrySolver
from arc.solvers.panels import PanelLogicSolver, PanelSelectSolver
from arc.solvers.scaling import DownscaleSolver, FractalTileSolver, TilingSolver, UpscaleSolver
from arc.solvers.symmetry import SymmetryRepairSolver

# Most constrained first; degenerate fallbacks last.
RULE_ORDER: tuple[type[RuleSolver], ...] = (
    IdentitySolver,
    GeometrySolver,
    ColourMapSolver,
    TilingSolver,
    FractalTileSolver,
    UpscaleSolver,
    DownscaleSolver,
    SymmetryRepairSolver,
    PanelLogicSolver,
    PanelSelectSolver,
    CropSolver,
    ConstantOutputSolver,
    ShapeFillSolver,
)


@register("composite")
class CompositeSolver:
    """Every rule that fits the demonstrations gets a vote, in priority order."""

    name = "composite"

    def __init__(self) -> None:
        self.rules: list[RuleSolver] = [rule() for rule in RULE_ORDER]

    def fitting_rules(self, task: Task) -> list[str]:
        """Names of the rules that explain this task's demonstrations, in priority order."""
        return [rule.name for rule in self.rules if rule.fits(task)]

    def fits(self, task: Task) -> bool:
        return any(rule.fits(task) for rule in self.rules)

    def solve(self, task: Task) -> list[Attempts]:
        fitted = [transform for rule in self.rules if (transform := rule.fit(task)) is not None]
        results: list[Attempts] = []
        for pair in task.test:
            proposals = [
                grid for transform in fitted if (grid := transform(pair.input)) is not None
            ]
            results.append(trim_attempts(proposals))
        return results
