"""The agent the competition runner plays — our policies behind its interface.

This file is what goes to Kaggle. `scripts/build_kaggle_notebook.py` writes it,
together with the `arcagi3` package it imports, into the submission notebook,
and `scripts/play_offline.py` imports it to play real games locally, so the two
cannot drift apart.

The runner (github.com/arcprize/ARC-AGI-3-Agents) must be importable as the
`agents` package; the notebook and play_offline.py both arrange that.
"""

from __future__ import annotations

from agents.agent import Agent
from arcengine import FrameData, GameState

from arcagi3.router import RoutingAgent
from arcagi3.sdk_adapter import SDKPolicyAdapter


class MyAgent(SDKPolicyAdapter, Agent):
    """Walks games that offer directions, clicks games that only take the mouse."""

    #: Per-game action cap. The runner stops a game at this many actions.
    #:
    #: Set from the scoring code (arc_agi.scorecard), not guessed: a level that
    #: is never cleared scores 0 however many actions it took, so extra actions
    #: can only help, and a level cleared late still scores
    #: min(115, 100 * (baseline / actions) ** 2) > 0. The price is time, against
    #: a 12-hour limit shared by every game. On recorded real boards this agent
    #: decides in 4 ms at the median and 25 ms at the 99th percentile
    #: (scripts/replay_traces.py); even at 30 ms an action including the game
    #: server, 100 games at 2,000 actions is 1.7 hours.
    MAX_ACTIONS = 2000

    policy_factory = RoutingAgent

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # Stop only on a win. GAME_OVER is answered with RESET and another try,
        # which is what the adapter's choose_action does.
        return latest_frame.state is GameState.WIN
