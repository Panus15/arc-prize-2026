"""Would deliberate probing learn the controls faster than incidental play?

The probe budget this project reports — roughly 40 to 80 actions — comes from
the winner's recorded runs, and that agent was not trying to establish what the
buttons do; it was trying to win. The number therefore measures incidental
exploration, not deliberate probing, and our own agent would choose differently.

Running our agent against a live game is the only fully honest comparison and
is not available. What is available is the same evidence in a different order:
taking each recorded run's movement transitions and feeding them round-robin
across the actions, the way a prober that samples evenly would see them, versus
the order they actually occurred. Same data, same learner, only the order
changes — which isolates exactly the effect in question.
"""

from __future__ import annotations

import argparse
import glob
import statistics
import sys
from collections import defaultdict

from arcengine import GameAction

from arcagi3.control import ControlLearner
from arcagi3.replay import LABEL_DIRECTION, Transition, game_id, read_transitions

DEFAULT_TRACES = (
    "/tmp/claude-0/-home-user-EcosyncAi/15b0ac55-f9c9-50da-9dfd-f72174a696dc"
    "/scratchpad/duck/example-run/artifacts"
)
BY_NAME: dict[str, GameAction] = {action.name: action for action in GameAction}

# Stop once the learner has been right about this many actions at once; below
# two, a "mapping" is not yet a mapping.
TARGET_ACTIONS = 2


def movement_transitions(path: str) -> list[tuple[GameAction, Transition]]:
    out: list[tuple[GameAction, Transition]] = []
    for transition in read_transitions(path):
        if not transition.is_movement_label or not transition.board_changed:
            continue
        action = BY_NAME.get(transition.action_name)
        if action is not None:
            out.append((action, transition))
    return out


def balanced(pairs: list[tuple[GameAction, Transition]]) -> list[tuple[GameAction, Transition]]:
    """The same transitions, cycling evenly through the actions.

    This is what a prober that samples each unknown action in turn would see,
    reconstructed from evidence that actually happened.
    """
    queues: dict[GameAction, list[tuple[GameAction, Transition]]] = defaultdict(list)
    for pair in pairs:
        queues[pair[0]].append(pair)
    order = sorted(queues, key=lambda a: a.value)
    out: list[tuple[GameAction, Transition]] = []
    while any(queues[action] for action in order):
        for action in order:
            if queues[action]:
                out.append(queues[action].pop(0))
    return out


def cost_to_learn(
    pairs: list[tuple[GameAction, Transition]], truth: dict[GameAction, tuple[int, int]]
) -> int | None:
    """Observations needed before the mapping is right about TARGET_ACTIONS."""
    learner = ControlLearner()
    for index, (action, transition) in enumerate(pairs, start=1):
        learner.observe(transition.before, transition.after, action)
        mapping = learner.mapping()
        correct = sum(1 for a, d in mapping.items() if truth.get(a) == d)
        if correct >= TARGET_ACTIONS and correct == len(mapping):
            return index
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recorded order versus even probing")
    parser.add_argument("--traces", default=DEFAULT_TRACES)
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    files = sorted(glob.glob(f"{args.traces}/*_p0_events.jsonl"))[: args.limit]
    if not files:
        print(f"no traces in {args.traces}", file=sys.stderr)
        return 2

    rows: list[tuple[str, int | None, int | None]] = []
    for index, path in enumerate(files, start=1):
        print(f"  [{index}/{len(files)}] {game_id(path)}", file=sys.stderr, flush=True)
        pairs = movement_transitions(path)
        if not pairs:
            continue
        truth = {action: LABEL_DIRECTION[transition.action_display] for action, transition in pairs}
        rows.append(
            (game_id(path), cost_to_learn(pairs, truth), cost_to_learn(balanced(pairs), truth))
        )

    print(f"\n{'game':<16} {'as recorded':>12} {'probed evenly':>14}")
    print("-" * 46)
    for game, recorded, even in rows:
        print(f"{game:<16} {str(recorded or '-'):>12} {str(even or '-'):>14}")

    both = [(r, e) for _, r, e in rows if r is not None and e is not None]
    print("-" * 46)
    if both:
        rec = [r for r, _ in both]
        eve = [e for _, e in both]
        print(f"{'median':<16} {int(statistics.median(rec)):>12} {int(statistics.median(eve)):>14}")
        faster = sum(1 for r, e in both if e < r)
        print(f"\ngames where even probing learned sooner: {faster}/{len(both)}")
        print(
            f"games learned at all: recorded {sum(1 for _, r, _ in rows if r)}/{len(rows)}, "
            f"even {sum(1 for _, _, e in rows if e)}/{len(rows)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
