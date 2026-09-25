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


class RoutingAgent(BaseAgent):
    """Delegates to a walker when directions are offered, else to a clicker."""

    name = "router"

    def __init__(
        self,
        walker: Callable[[], BaseAgent] = walker,
        clicker: Callable[[], BaseAgent] = ClickAgent,
    ) -> None:
        self._walker = walker
        self._clicker = clicker
        self.chosen: BaseAgent | None = None

    def _pick(self, latest: FrameData) -> BaseAgent | None:
        offered = set(latest.available_actions or ())
        if offered & DIRECTIONS:
            return self._walker()
        if CLICK in offered:
            return self._clicker()
        return None  # nothing informative yet; decide on a later frame

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        if self.chosen is None:
            self.chosen = self._pick(latest)
        if self.chosen is None:
            # Neither kind offered: whatever is legal, never a click with no target.
            offered = [a for a in latest.available_actions if a != CLICK]
            return GameAction.RESET if not offered else action_from_value(min(offered))
        return self.chosen.choose_action(frames, latest)

    def is_done(self, frames: list[FrameData], latest: FrameData) -> bool:
        return latest.state is GameState.WIN

    def mouse_target(self) -> tuple[int, int] | None:
        """Where the delegate's last click points, for the SDK adapter."""
        ask = getattr(self.chosen, "mouse_target", None)
        return None if ask is None else ask()
