"""Action vocabulary, and the safe way to turn a frame's integers into actions.

`FrameData.available_actions` arrives as a list of plain integers, but
`GameAction` cannot be constructed from one: its value-to-member map is keyed by
`(value, action_class)` tuples, so `GameAction(1)` raises. Everything that reads
`available_actions` has to go through `action_from_value` instead.
"""

from __future__ import annotations

from arcengine import GameAction

# Movement actions as (dy, dx). ACTION5 is "interact" in the mock game.
MOVES: dict[GameAction, tuple[int, int]] = {
    GameAction.ACTION1: (-1, 0),
    GameAction.ACTION2: (1, 0),
    GameAction.ACTION3: (0, -1),
    GameAction.ACTION4: (0, 1),
}
INTERACT = GameAction.ACTION5

# ACTION6 is the one ComplexAction in the enum; the others are SimpleAction.
# Complex actions carry payload in ActionInput.data (coordinates), so a policy
# cannot emit one by picking the bare enum member.
COMPLEX_ACTIONS: frozenset[GameAction] = frozenset({GameAction.ACTION6})

# What each action means in the games, confirmed against the Milestone #1
# winner's action_names.py. ACTION7 appears in the enum but is not mapped there,
# so its meaning is still unknown.
ACTION_MEANING: dict[GameAction, str] = {
    GameAction.RESET: "RESET",
    GameAction.ACTION1: "UP",
    GameAction.ACTION2: "DOWN",
    GameAction.ACTION3: "LEFT",
    GameAction.ACTION4: "RIGHT",
    GameAction.ACTION5: "SPACE",
    GameAction.ACTION6: "MOUSE",
}


def describe(action: GameAction) -> str:
    """Human-readable name for logs and traces."""
    return ACTION_MEANING.get(action, action.name)


_BY_VALUE: dict[int, GameAction] = {action.value: action for action in GameAction}


def action_from_value(value: int) -> GameAction:
    """Map an integer out of `available_actions` back to its GameAction."""
    try:
        return _BY_VALUE[value]
    except KeyError:
        raise ValueError(f"{value} is not a GameAction value") from None


def actions_from_values(values: list[int]) -> list[GameAction]:
    """Map a whole `available_actions` list, preserving order."""
    return [action_from_value(v) for v in values]
