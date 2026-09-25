"""Driving our policies from the official ARC-AGI-3-Agents runner.

The competition ships its own agent framework (github.com/arcprize/ARC-AGI-3-Agents).
Its `agents.agent.Agent` base class handles recording, tracing and `take_action`,
and asks a subclass for exactly two methods. That base class is not on PyPI — it
lives only in that repo — so this module does not import it. It provides a mixin
that answers those two methods instead, so mixing it into a subclass there works
without touching any policy code.

Drop this file's adapter into a checkout of ARC-AGI-3-Agents like so:

    # ARC-AGI-3-Agents/agents/templates/arcagi3_navigator.py
    from arcagi3.navigator import NavigatorAgent
    from arcagi3.sdk_adapter import SDKPolicyAdapter

    from ..agent import Agent


    class Navigator(SDKPolicyAdapter, Agent):
        \"\"\"Our policy, driven by the official runner.\"\"\"

        MAX_ACTIONS = 200
        policy_factory = NavigatorAgent

Then import `Navigator` in `agents/__init__.py` — `AVAILABLE_AGENTS` is built
from `Agent.__subclasses__()`, so the import alone registers it under its
lower-cased class name — and run it with our `agi3/` directory on `PYTHONPATH`:

    PYTHONPATH=/path/to/arc-prize-2026/agi3 uv run main.py --agent=navigator --game=ls20

The mixin must come first in the bases so its concrete `is_done` and
`choose_action` satisfy the ABC. It defines no `__init__`, so it never has to
cooperate with the SDK's constructor signature.

What the adapter fixes up between the real API and our policies:

* `FrameData.frame` is a stack of grids, and our policies read a single board.
* the real API offers a different action set per frame, and spending an action
  the game refuses is pure waste.
* `ACTION6` needs a coordinate payload that a bare `GameAction` cannot carry.
* that payload lives on the `GameAction` enum member, one object shared by
  every agent in the process, and the runner's `Swarm` plays every game on its
  own thread at once — so each agent sends the coordinates it chose itself.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol, runtime_checkable

from arcengine import FrameData, GameAction, GameState
from arcengine.enums import ComplexAction

from arcagi3.actions import COMPLEX_ACTIONS, action_from_value
from arcagi3.agent import BaseAgent
from arcagi3.navigator import NavigatorAgent

Grid = list[list[int]]

# `ComplexAction` bounds x and y to 0..63, and the engine's camera renders 64x64.
BOARD_SIZE = 64


@runtime_checkable
class PointingPolicy(Protocol):
    """A policy that can also say where its last chosen action points.

    Optional: the adapter asks for a target only when the policy just chose a
    complex action, and only when it has this method at all, so the policies
    that never emit ACTION6 need no changes.
    """

    def mouse_target(self) -> tuple[int, int] | None:
        """Grid (row, col) for the complex action just returned, or None."""


def board_from_frame(frame_data: FrameData) -> Grid | None:
    """The settled board out of a frame stack, or None when there is none.

    `frame` is a stack because `ARCBaseGame.action` loops `while not
    is_action_complete()`, rendering once per engine step and appending each
    render. The stack is therefore an animation of one action resolving, not
    layers of one screen — `arc_agi.rendering.render_frames` plays it back at an
    FPS, which is only meaningful for a time series. So the *last* layer is the
    board the next action acts on, and index 0 is a mid-animation snapshot.

    That is read off the local engine's source; the remote server returns the
    same schema but has not been checked against a live game, so a real game
    sending its layers in some other order would break this assumption.

    Trailing empty layers are skipped rather than treated as an empty board, and
    a missing stack yields None: the engine returns `frame=[]` on WIN and
    GAME_OVER, and the SDK seeds its history with an empty `FrameData` before the
    first action, so "no board" is a normal state, not a malformed one.
    """
    stack = frame_data.frame or []
    for layer in reversed(stack):
        if layer:
            return layer
    return None


def normalise_frame(frame_data: FrameData) -> FrameData:
    """A copy of the frame whose stack holds only the settled board.

    Our policies index `frame[0]`, which on a real multi-layer stack is a
    mid-animation render. Collapsing the stack before the policy sees it makes
    `frame[0]` and `frame[-1]` the same correct grid, so the policies keep
    working unchanged. The board list is reused rather than copied — this runs
    once per historical frame per action, and 64x64 copies would add up.
    """
    board = board_from_frame(frame_data)
    if board is None:
        return frame_data
    return frame_data.model_copy(update={"frame": [board]})


def legal_actions(frame_data: FrameData) -> list[GameAction]:
    """`available_actions` as GameActions, in the order the frame listed them.

    Values the installed enum does not know are dropped rather than raising: a
    server that adds an action should cost us the option, not the run.
    """
    actions = []
    for value in frame_data.available_actions or []:
        try:
            actions.append(action_from_value(value))
        except ValueError:
            continue
    return actions


def fallback_action(
    available: Sequence[GameAction],
    *,
    exclude: Iterable[GameAction] = (),
) -> GameAction:
    """Lowest-valued usable action, or RESET when nothing else is offered.

    Sorted by `value`, never by iterating a set of GameAction: enum members hash
    by identity, so set order changes between processes and the same board would
    otherwise produce different play on different runs. Membership tests against
    a set are fine — only the iteration order is unstable.
    """
    skip = frozenset(exclude)
    usable = sorted(
        (a for a in available if a is not GameAction.RESET and a not in skip),
        key=lambda a: a.value,
    )
    return usable[0] if usable else GameAction.RESET


def mouse_action(row: int, col: int) -> GameAction:
    """ACTION6 carrying a click at grid (row, col).

    The engine takes a click as x/y while every grid in this codebase is indexed
    (row, col), and `ARCBaseGame.get_pixels` slices `frame[y:y+h, x:x+w]` — so y
    is the row and x is the column. The flip lives here and nowhere else.

    Raises ValueError off the board rather than clamping: a clamped click is a
    wasted action pointed at the wrong cell, which the scorecard counts.
    """
    if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
        raise ValueError(f"({row}, {col}) is outside the {BOARD_SIZE}x{BOARD_SIZE} board")
    action = GameAction.ACTION6
    # Payload rides on the shared enum member because that is the SDK's
    # contract: its `do_action_request` reads `action.action_data` off whatever
    # member the agent returned. It is process-global state, so it is set at the
    # moment of return and never relied on afterwards.
    action.set_data({"x": col, "y": row})
    return action


class SDKPolicyAdapter:
    """Answers the SDK `Agent`'s two abstract methods from one of our policies."""

    #: Builds the policy on first use. Any zero-argument callable returning a
    #: BaseAgent works; subclasses usually just name a policy class.
    policy_factory: Callable[[], BaseAgent] = NavigatorAgent

    #: Where to click when a complex action is the only thing on offer and the
    #: policy named no target. The board centre is a guess, but a legal action
    #: beats forfeiting the turn.
    default_mouse_target: tuple[int, int] = (BOARD_SIZE // 2, BOARD_SIZE // 2)

    @property
    def policy(self) -> BaseAgent:
        """The wrapped policy, built lazily on first access.

        Lazy so the mixin needs no `__init__` and cannot collide with the SDK
        `Agent.__init__` signature, which takes seven arguments and may change.
        """
        policy = getattr(self, "_policy", None)
        if policy is None:
            # Read off the class, not the instance: a plain function assigned to
            # `policy_factory` would bind as a method and be handed `self`.
            policy = type(self).policy_factory()
            self._policy = policy
        return policy

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        """Stop on a finished game. Override in the subclass to keep playing."""
        return self.policy.is_done(frames, latest_frame)

    def choose_action(self, frames: list[FrameData], latest_frame: FrameData) -> GameAction:
        """The policy's choice, corrected to something the frame actually offers."""
        available = legal_actions(latest_frame)

        # Before the first action, and after a finished game, there is no board:
        # the only move that can change that is RESET.
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET

        board = board_from_frame(latest_frame)
        if board is None or not available:
            # Nothing to reason about, or nothing offered. Never call the policy
            # here: ours read `frame[0]` and would raise on an empty stack.
            return fallback_action(available, exclude=COMPLEX_ACTIONS)

        chosen = self.policy.choose_action(
            [normalise_frame(frame) for frame in frames],
            normalise_frame(latest_frame),
        )
        if chosen not in available:
            # The SDK does not check this, and the game charges for the attempt.
            chosen = fallback_action(available)
        return self._with_payload(chosen, available)

    def _with_payload(self, chosen: GameAction, available: Sequence[GameAction]) -> GameAction:
        """Attach a click target to a complex action, or pick something simpler."""
        self._click = None
        if chosen not in COMPLEX_ACTIONS:
            return chosen

        target = self._mouse_target()
        if target is not None:
            try:
                return self._clicking(*target)
            except ValueError:
                pass  # off-board target: treat it as no target at all

        simple = fallback_action(available, exclude=COMPLEX_ACTIONS)
        if simple is not GameAction.RESET or GameAction.RESET in available:
            return simple
        return self._clicking(*self.default_mouse_target)

    def _clicking(self, row: int, col: int) -> GameAction:
        """`mouse_action`, with the target also kept on this agent."""
        action = mouse_action(row, col)
        self._click = (row, col)
        return action

    def do_action_request(self, action: GameAction) -> FrameData:
        """Send a click with the coordinates this agent chose, not the shared ones.

        The runner's own version reads the payload off the `GameAction` member,
        which every agent in the process shares. `Swarm` gives each game its own
        thread, so between one agent setting its click and the runner reading it
        back, another game's agent can overwrite it — the click then lands where
        a different game wanted it. Both environment wrappers take the payload
        as an argument, so passing ours explicitly removes the shared read.

        Anything that is not one of our clicks goes through the runner unchanged.
        """
        click = getattr(self, "_click", None)
        env = getattr(self, "arc_env", None)
        convert = getattr(self, "_convert_raw_frame_data", None)
        if action not in COMPLEX_ACTIONS or click is None or env is None or convert is None:
            # Not our click, or a runner version without these hooks: its own path.
            return super().do_action_request(action)  # type: ignore[misc]
        row, col = click
        data = ComplexAction(x=col, y=row).model_dump()
        return convert(env.step(action, data=data, reasoning=None))

    def _mouse_target(self) -> tuple[int, int] | None:
        """Ask the policy where its complex action points, if it can say."""
        ask = getattr(self.policy, "mouse_target", None)
        if ask is None:
            return None
        return ask()
