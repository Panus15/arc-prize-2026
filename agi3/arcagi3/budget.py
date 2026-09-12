"""Running an agent against an environment, and counting what it spent.

The competition's scorecard reports `level_actions` against
`level_baseline_actions`, so completion alone says little. These helpers report
both, and the ratio between them, which is the number a policy has to move.
"""

from __future__ import annotations

from dataclasses import dataclass

from arcengine import FrameData, GameState

from arcagi3.agent import BaseAgent
from arcagi3.mock import MockEnvironment


@dataclass(frozen=True)
class RunResult:
    """What one episode cost."""

    agent: str
    state: GameState
    levels_completed: int
    total_levels: int
    actions_used: int
    baseline_actions: int
    truncated: bool

    @property
    def won(self) -> bool:
        return self.state is GameState.WIN

    @property
    def efficiency(self) -> float | None:
        """Baseline actions per action spent. 1.0 is a perfect run, less is worse.

        None when nothing was spent, which would otherwise divide by zero.
        """
        if self.actions_used == 0:
            return None
        return self.baseline_actions / self.actions_used

    def summary(self) -> str:
        eff = "n/a" if self.efficiency is None else f"{self.efficiency:.2%}"
        outcome = "WIN" if self.won else ("truncated" if self.truncated else self.state.name)
        return (
            f"{self.agent:<10} {outcome:<10} "
            f"levels {self.levels_completed}/{self.total_levels}  "
            f"actions {self.actions_used} (baseline {self.baseline_actions}, efficiency {eff})"
        )


def run_episode(
    agent: BaseAgent,
    env: MockEnvironment | None = None,
    *,
    max_actions: int = 500,
) -> RunResult:
    """Play one episode, stopping at a win, a loss, or `max_actions`.

    The cap exists because a policy that never reaches the target would
    otherwise loop forever; hitting it is reported as `truncated` rather than
    being quietly folded into a loss.
    """
    env = env or MockEnvironment()
    latest: FrameData = env.reset()
    frames: list[FrameData] = [latest]
    truncated = False

    while not agent.is_done(frames, latest):
        if env.actions_used >= max_actions:
            truncated = True
            break
        latest = env.step(agent.act(frames, latest))
        frames.append(latest)

    return RunResult(
        agent=agent.name,
        state=latest.state,
        levels_completed=latest.levels_completed,
        total_levels=latest.win_levels,
        actions_used=env.actions_used,
        baseline_actions=env.optimal_actions,
        truncated=truncated,
    )
