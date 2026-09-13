"""A policy that works out what the buttons do before trying to use them.

Nothing tells an agent that ACTION1 means "up". The mapping is stable across
the official games, but hard-coding it makes a policy that cannot survive a
game where the controls differ — and it skips the part worth measuring: how
cheaply an agent can establish action semantics for itself.

This policy spends a few actions probing, watches the board through the
segmentation diff to see what each one did, and then navigates with what it
learned. The probe budget is the price; the learned map is the asset.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from arcengine import FrameData, GameAction

from arcagi3.actions import actions_from_values, describe
from arcagi3.agent import BaseAgent
from arcagi3.effects import Delta, diff
from arcagi3.perception import Node, Segmentation, segment


@dataclass
class ActionModel:
    """What each action has been observed to do."""

    effects: dict[GameAction, Delta] = field(default_factory=dict)
    inert: set[GameAction] = field(default_factory=set)

    def record(self, action: GameAction, delta: Delta | None, *, board_changed: bool) -> None:
        """Note the outcome of one probe.

        An action is only called inert when the board genuinely did not move.
        A busy frame — a level transition, several objects shifting at once —
        leaves the effect unattributable, which is not evidence of inertness and
        must not overwrite what an earlier clean probe established.
        """
        if delta is not None:
            self.effects[action] = delta
            self.inert.discard(action)
        elif not board_changed and action not in self.effects:
            self.inert.add(action)

    def known(self, action: GameAction) -> bool:
        return action in self.effects or action in self.inert

    def action_for(self, direction: Delta) -> GameAction | None:
        """The action whose observed effect points the way, if one does."""
        for action, delta in self.effects.items():
            if _unit(delta) == direction:
                return action
        return None

    def summary(self) -> str:
        learned = ", ".join(
            f"{describe(a)}={d[0]:+d},{d[1]:+d}"
            for a, d in sorted(self.effects.items(), key=lambda kv: kv[0].value)
        )
        return learned or "(nothing learned)"


class ExplorerAgent(BaseAgent):
    """Probe unknown actions, then steer the object that turned out to move."""

    name = "explorer"

    def __init__(self, interact: GameAction = GameAction.ACTION5) -> None:
        self.model = ActionModel()
        self._interact = interact
        self._previous: Segmentation | None = None
        self._pending: GameAction | None = None
        self._controlled: str | None = None
        self._goal_colours: set[int] = set()
        self._stuck: dict[int, int] = {}

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        board = segment(latest.frame[0])
        available = actions_from_values(latest.available_actions)
        self._learn_from(board, available)
        useful = [a for a in available if a is not GameAction.RESET]

        # An interaction on offer is almost always the point of being here, and
        # it is one action rather than a search, so it is never worth deferring.
        if self._interact in available:
            return self._commit(self._interact, board)

        unknown = [a for a in useful if not self.model.known(a) and a is not self._interact]
        if unknown:
            return self._commit(unknown[0], board)

        planned = self._navigate(board, useful)
        return self._commit(planned or (useful[0] if useful else GameAction.RESET), board)

    # --- learning ----------------------------------------------------------

    def _learn_from(self, board: Segmentation, available: list[GameAction]) -> None:
        """Attribute the last action's effect, when the board makes it unambiguous."""
        if self._pending is None or self._previous is None:
            return
        change = diff(self._previous, board)
        movement = change.sole_movement()
        self.model.record(self._pending, movement, board_changed=change.changed)
        if movement is not None:
            moved = change.moved[0]
            if moved.after is not None:
                # Whatever moved when we pressed a button is what we are steering.
                self._controlled = moved.after.hash

        # Learning what a goal looks like: an interaction becoming available
        # right as an object disappeared under us identifies that object's
        # colour as worth walking to. Without this, "nearest object" sends the
        # agent to the nearest wall instead.
        if self._interact in available:
            for gone in change.vanished:
                if gone.before is not None:
                    self._goal_colours.add(gone.before.colour)
        self._pending = None

    def _commit(self, action: GameAction, board: Segmentation) -> GameAction:
        self._previous = board
        self._pending = action
        return action

    # --- acting ------------------------------------------------------------

    def _navigate(self, board: Segmentation, useful: list[GameAction]) -> GameAction | None:
        me = self._controlled_node(board)
        goal = self._nearest_other(board, me)
        if me is None or goal is None:
            return None

        dr = goal.top_left[0] - me.top_left[0]
        dc = goal.top_left[1] - me.top_left[1]
        # Close the larger gap first, but accept the other axis if the game will
        # not let us move that way right now.
        order = [(_sign(dr), 0), (0, _sign(dc))]
        if abs(dc) > abs(dr):
            order.reverse()
        for direction in order:
            if direction == (0, 0):
                continue
            action = self.model.action_for(direction)
            if action is not None and action in useful:
                return action
        return None

    def _controlled_node(self, board: Segmentation) -> Node | None:
        if self._controlled is None:
            return None
        for node in board.nodes:
            if node.hash == self._controlled:
                return node
        return None

    def _nearest_other(self, board: Segmentation, me: Node | None) -> Node | None:
        """Nearest object worth walking to, preferring ones that look like goals."""
        if me is None:
            return None
        others = [n for n in board.nodes if n.id != me.id]
        if self._goal_colours:
            goals = [n for n in others if n.colour in self._goal_colours]
            others = goals or others
        if not others:
            return None
        return min(
            others,
            key=lambda n: abs(n.top_left[0] - me.top_left[0]) + abs(n.top_left[1] - me.top_left[1]),
        )


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _unit(delta: Delta) -> Delta:
    return _sign(delta[0]), _sign(delta[1])
