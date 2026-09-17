"""A policy built from the parts that survived contact with real games.

`ExplorerAgent` learns the controls by requiring a single unambiguous object
movement, which works on a tidy board and almost never fires on a real one
(0.4% of recorded transitions). This one uses the centroid-based
`ControlLearner` instead, routes with shortest-path search rather than walking
two legs of an L, and learns which colours block movement by bumping into them.

It also decides when to stop exploring using the measured confidence signal:
below the threshold the learned mapping is right about 79% of the time, above
0.65 about 91%, so acting on a low-confidence map mostly spends actions the
scorecard counts for nothing.
"""

from __future__ import annotations

from collections import Counter, deque

from arcengine import FrameData, GameAction

from arcagi3.actions import actions_from_values
from arcagi3.agent import BaseAgent
from arcagi3.control import ControlLearner
from arcagi3.navigation import ObstacleModel, find_path
from arcagi3.perception import segment

# Measured across 500 recorded runs: below 0.6 the learned mapping is 36%
# accurate, just above it 84%, and the top band only 85% — so the cliff is at
# 0.6 and waiting for more buys accuracy that is not there. See
# docs/control-learning-curve.md.
TRUST_THRESHOLD = 0.6

# How many recent predictions to judge the mapping by, and how many of them may
# fail before it is discarded. One miss is ordinary — something blocked the way,
# or the level changed under us — but a map that keeps mispredicting is worse
# than none: the agent follows it and spends actions the scorecard counts. One
# recorded game produced a mapping on all 20 passes and was wrong on every one.
PREDICTION_WINDOW = 8
MIN_PREDICTION_HITS = 3

Grid = list[list[int]]
Cell = tuple[int, int]


class NavigatorAgent(BaseAgent):
    """Probe until the controls are trustworthy, then walk a planned route."""

    name = "navigator"

    def __init__(
        self,
        interact: GameAction = GameAction.ACTION5,
        trust: float = TRUST_THRESHOLD,
    ) -> None:
        self.control = ControlLearner()
        self.obstacles = ObstacleModel()
        self._interact = interact
        self._trust = trust
        self._goal_colours: set[int] = set()
        self._before: Grid | None = None
        self._pending: GameAction | None = None
        self._tried: Counter[GameAction] = Counter()
        self._predictions: deque[bool] = deque(maxlen=PREDICTION_WINDOW)
        self._expected: tuple[Cell, Cell] | None = None
        self.resets = 0

    def choose_action(self, frames: list[FrameData], latest: FrameData) -> GameAction:
        board = latest.frame[0]
        available = actions_from_values(latest.available_actions)
        self._learn(board, available)

        if self._interact in available:
            return self._commit(self._interact, board)

        movers = [a for a in available if a is not GameAction.RESET and a is not self._interact]
        if not movers:
            return self._commit(GameAction.RESET, board)

        mapping = self.control.mapping()
        ready = self.control.confidence() >= self._trust and len(mapping) >= 2
        if not ready:
            return self._commit(self._probe(movers), board)

        planned = self._route(board, movers)
        return self._commit(planned or self._probe(movers), board)

    # --- learning ----------------------------------------------------------

    def _learn(self, board: Grid, available: list[GameAction]) -> None:
        if self._pending is None or self._before is None:
            return
        action, before = self._pending, self._before
        self._pending = None

        if action not in (GameAction.RESET, self._interact):
            self._check_prediction(board)
            self.control.observe(before, board, action)
            self._note_obstacle(before, board, action)

        if self._interact in available:
            self._note_goal(before, board)

        self._note_walls(board, available)

    def _note_walls(self, board: Grid, available: list[GameAction]) -> None:
        """Read obstacles off the availability list.

        A game that refuses a direction outright never lets the agent bump into
        the wall, so waiting for a failed move learns nothing. But a known
        direction missing from `available_actions` says exactly the same thing:
        whatever occupies the cell that way is not enterable. The real API ships
        `available_actions` per frame too, so this reads the same signal there.
        """
        player = self._player_cell(board)
        if player is None:
            return
        offered = set(available)
        for action, step in self.control.mapping().items():
            ahead = (player[0] + step[0], player[1] + step[1])
            if not (0 <= ahead[0] < len(board) and 0 <= ahead[1] < len(board[0])):
                continue  # off the board, not a wall
            colour = board[ahead[0]][ahead[1]]
            if action in offered:
                self.obstacles.record_passable(colour)
            else:
                self.obstacles.record_blocked(colour)

    def _check_prediction(self, board: Grid) -> None:
        """Hold the mapping to account, and abandon it when it stops paying out.

        The test is whether the player moved the way the map said, not whether
        it landed on the exact square. An animating sprite drags its centroid
        sideways, so a map that is entirely correct still misses the square by a
        cell most of the time — judging on exact position discards good maps
        constantly. Direction still catches the failure this exists for: a map
        that does not describe the game sends the player the wrong way, which
        scores no progress at all.
        """
        if self._expected is None:
            return
        (before, predicted), self._expected = self._expected, None
        actual = self._player_cell(board)
        if actual is None:
            return
        wanted = (predicted[0] - before[0], predicted[1] - before[1])
        moved = (actual[0] - before[0], actual[1] - before[1])
        progress = wanted[0] * moved[0] + wanted[1] * moved[1]
        self._predictions.append(progress > 0)

        if len(self._predictions) < PREDICTION_WINDOW:
            return
        if sum(self._predictions) >= MIN_PREDICTION_HITS:
            return

        # The map does not describe this game. Keep what was learned about
        # walls — obstacles do not stop being obstacles because the controls
        # were misread — and learn the controls again from nothing.
        self.control = ControlLearner()
        self._predictions.clear()
        self._tried.clear()
        self.resets += 1

    def _note_obstacle(self, before: Grid, after: Grid, action: GameAction) -> None:
        """A refused move names what is in the way.

        Only a completely unchanged board counts: if anything moved, the action
        did something and the cell ahead is not necessarily a wall.
        """
        if before != after:
            player = self._player_cell(after)
            if player is not None:
                self.obstacles.record_passable(after[player[0]][player[1]])
            return
        step = self.control.mapping().get(action)
        player = self._player_cell(before)
        if step is None or player is None:
            return
        ahead = (player[0] + step[0], player[1] + step[1])
        if 0 <= ahead[0] < len(before) and 0 <= ahead[1] < len(before[0]):
            self.obstacles.record_blocked(before[ahead[0]][ahead[1]])

    def _note_goal(self, before: Grid, after: Grid) -> None:
        """Whatever we covered up as an interaction became available is a goal."""
        gone = _colours(before) - _colours(after)
        self._goal_colours |= gone

    # --- acting ------------------------------------------------------------

    def _probe(self, movers: list[GameAction]) -> GameAction:
        """Sample whichever action is least understood.

        Actions with no learned effect come first — routing fails the moment the
        path needs a direction that was never established, so an unknown action
        is worth more than another sample of a known one. Ties break by action
        value to keep play reproducible.
        """
        mapping = self.control.mapping()
        unknown = [a for a in movers if a not in mapping]
        pool = unknown or movers
        return min(pool, key=lambda a: (self._tried[a], a.value))

    def _route(self, board: Grid, movers: list[GameAction]) -> GameAction | None:
        player = self._player_cell(board)
        goal = self._goal_cell(board, player)
        if player is None or goal is None:
            return None

        path = find_path(board, player, goal, self.obstacles)
        if not path:
            return None
        # Ask for the best available action along the next step rather than an
        # exact match: a learned effect is not always a clean cardinal step.
        return self.control.best_action_for(path[0], movers)

    def _player_cell(self, board: Grid) -> Cell | None:
        """Where the controlled object is, as its centre of mass.

        Taking the first matching cell breaks on a sprite that animates: it
        occupies more than one cell and the extra one is sometimes scanned
        first, so the reported position jumps by a cell for no reason. Routing
        then plans from the wrong square and the prediction check reads the
        mismatch as a broken mapping. The centroid is what the control learner
        already tracks, so using it here keeps the two consistent.
        """
        colour = self.control.controlled_colour()
        if colour is None:
            return None
        rows = cols = count = 0
        for r, row in enumerate(board):
            for c, value in enumerate(row):
                if value == colour:
                    rows += r
                    cols += c
                    count += 1
        if count == 0:
            return None
        return round(rows / count), round(cols / count)

    def _goal_cell(self, board: Grid, player: Cell | None) -> Cell | None:
        if player is None:
            return None
        seg = segment(board)
        candidates = [
            n
            for n in seg.nodes
            if n.colour != self.control.controlled_colour()
            # A wall is scenery to route around, never somewhere to route to.
            and not self.obstacles.is_blocked(n.colour)
        ]
        if self._goal_colours:
            preferred = [n for n in candidates if n.colour in self._goal_colours]
            candidates = preferred or candidates
        if not candidates:
            return None
        nearest = min(
            candidates,
            key=lambda n: abs(n.top_left[0] - player[0]) + abs(n.top_left[1] - player[1]),
        )
        return nearest.top_left

    def _commit(self, action: GameAction, board: Grid) -> GameAction:
        self._before = [row[:] for row in board]
        self._pending = action
        self._tried[action] += 1
        self._expected = self._predict(board, action)
        return action

    def _predict(self, board: Grid, action: GameAction) -> tuple[Cell, Cell] | None:
        """Where the player is now, and where the mapping says it will be."""
        step = self.control.mapping().get(action)
        player = self._player_cell(board)
        if step is None or player is None:
            return None
        return player, (player[0] + step[0], player[1] + step[1])


def _colours(board: Grid) -> set[int]:
    return {value for row in board for value in row}
