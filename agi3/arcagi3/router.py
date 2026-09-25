"""Choose the walking or the clicking policy from what a game offers.

Eight of the 25 public games are played almost entirely with MOUSE and never
once with a direction; the rest are walked. A submission plays every game with
one agent class, so something has to pick. The frame already says which kind
of game it is — `available_actions` — so the choice is made from that, once,
on the first frame that has any, and kept for the rest of the game.
"""

from __future__ import annotations

from collections.abc import Callable

from arcengine import FrameData, GameAction, GameState

from arcagi3.actions import action_from_value
from arcagi3.agent import BaseAgent
from arcagi3.clicker import ClickAgent
from arcagi3.navigator import NavigatorAgent

DIRECTIONS = frozenset(
    action.value
    for action in (GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4)
)
CLICK = GameAction.ACTION6.value


def walker() -> BaseAgent:
    """The navigator with the `fallback` estimator.

    Of the three estimators it is the only one that clears every mock arena,
    including noise with a fixed action list and scrambled controls (see
    docs/static-actions.md), at a cost of two points of mapping accuracy on
    recorded real boards: 77% against the centroid's 79%.
    """
    return NavigatorAgent(estimator="fallback")


# Actions without a new level before the other mode is tried, in a game that
# offers both. In the recordings of lf52, which offers directions and clicks,
# all 15 level completions came from clicks: routing by the offer alone would
# have walked it forever. An uncleared level scores 0 at any action count, so
# trying the other mode costs only levels that were already going badly — a
# level cleared after 300 actions scores (baseline / 300)^2 of its maximum.
# 300 itself is a judgement, not a measurement; revisit it on real games.
STALL_BUDGET = 300


class RoutingAgent(BaseAgent):
    """Walks when directions are offered, clicks when only the mouse is, and
    tries the other of the two when one stops producing levels."""

    name = "router"

    def __init__(
        self,
        walker: Callable[[], BaseAgent] = walker,
        clicker: Callable[[], BaseAgent] = ClickAgent,
        stall_budget: int = STALL_BUDGET,
    ) -> None:
        self._factories = {"walk": walker, "click": clicker}
        self._instances: dict[str, BaseAgent] = {}
        self._modes: list[str] = []
        self._mode = 0
        self._stall_budget = stall_budget
        self._since_progress = 0
        self._level = 0
        self.switches = 0
        self.chosen: BaseAgent | None = None
        #: Names of the policies used, in the order first used.
        self.used: list[str] = []

    def _plan(self, latest: FrameData) -> list[str]:
        offered = set(latest.available_actions or ())
        modes = []
        if offered & DIRECTIONS:
            modes.append("walk")
        if CLICK in offered:
            modes.append("click")
        return modes

    def _use(self, mode: str) -> BaseAgent:
        # Kept, not rebuilt: coming back to a mode resumes what it had learned.
        if mode not in self._instances:
            self._instances[mode] = self._factories[mode]()
            self.used.append(self._instances[mode].name)
        self.chosen = self._instances[mode]
        return self.chosen

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        if not self._modes:
            self._modes = self._plan(latest)
            if not self._modes:
                # Neither kind offered: whatever is legal, never a click with no target.
                offered = [a for a in latest.available_actions if a != CLICK]
                return GameAction.RESET if not offered else action_from_value(min(offered))
            self._use(self._modes[0])

        if latest.levels_completed != self._level:
            self._level = latest.levels_completed
            self._since_progress = 0
        elif len(self._modes) > 1 and self._since_progress >= self._stall_budget:
            self._mode = (self._mode + 1) % len(self._modes)
            self._since_progress = 0
            self.switches += 1
            self._use(self._modes[self._mode])
        self._since_progress += 1

        assert self.chosen is not None
        return self.chosen.choose_action(frames, latest)

    def is_done(self, frames: list[FrameData], latest: FrameData) -> bool:
        return latest.state is GameState.WIN

    def mouse_target(self) -> tuple[int, int] | None:
        """Where the delegate's last click points, for the SDK adapter."""
        ask = getattr(self.chosen, "mouse_target", None)
        return None if ask is None else ask()
