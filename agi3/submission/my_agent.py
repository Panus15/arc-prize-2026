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
    MAX_ACTIONS = 400

    policy_factory = RoutingAgent

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        # Stop only on a win. GAME_OVER is answered with RESET and another try,
        # which is what the adapter's choose_action does.
        return latest_frame.state is GameState.WIN
