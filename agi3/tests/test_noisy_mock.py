"""Tests for the environment that reproduces measured board noise.

Two methods have now passed against a quiet mock and failed on recorded games.
This environment exists so that stops happening silently, and these tests pin
both its properties and what the current policies do against it — including
what they fail to do.
"""

from __future__ import annotations

from arcengine import GameAction

from arcagi3.agent import GreedyAgent
from arcagi3.budget import run_episode
from arcagi3.control import ControlLearner
from arcagi3.explorer import ExplorerAgent
from arcagi3.mock import MockEnvironment
from arcagi3.navigator import NavigatorAgent
from arcagi3.noisy_mock import HUD_COLOUR, NoisyEnvironment


def test_nearly_every_action_changes_the_board():
    """Measured on real click games: 91% to 100%. A quiet mock hid that."""
    env = NoisyEnvironment()
    frame = env.reset()
    previous = frame.frame[0]
    changed = 0
    for step in range(40):
        frame = env.step(GameAction.ACTION2 if step % 2 else GameAction.ACTION4)
        changed += frame.frame[0] != previous
        previous = frame.frame[0]
    assert changed >= 36


def test_the_hud_advances_on_every_action_including_refused_ones():
    """A timer cannot be told from gameplay by whether it moved."""
    env = NoisyEnvironment()
    env.reset()
    first = env.step(GameAction.ACTION1).frame[0][-1]  # up, off the board
    second = env.step(GameAction.ACTION1).frame[0][-1]
    assert first != second


def test_the_hud_is_a_strip_against_an_edge():
    row = NoisyEnvironment().reset().frame[0][-1]
    assert HUD_COLOUR in row


def test_the_sprite_changes_shape_between_frames():
    """The thing that made object-hash matching lose the player on real boards."""
    env = NoisyEnvironment()
    env.reset()
    sizes = set()
    for _ in range(4):
        frame = env.step(GameAction.ACTION2)
        sizes.add(sum(row.count(4) for row in frame.frame[0]))
    assert len(sizes) > 1


def test_noise_can_be_turned_off():
    env = NoisyEnvironment(hud=False, animate=False)
    plain = MockEnvironment()
    assert len(env.reset().frame[0]) == len(plain.reset().frame[0])


def test_a_hard_coded_policy_is_untouched_by_the_noise():
    """It never learns anything, so there is nothing for noise to corrupt."""
    assert run_episode(GreedyAgent(), NoisyEnvironment(), max_actions=400).won


def test_the_learned_effects_become_diagonal_under_an_animating_sprite():
    """The mechanism behind the failure, pinned so it is not rediscovered.

    The blur sits beside the cursor, so the colour's centroid moves sideways as
    well as forward and the learned effect records a diagonal. It shows up when
    directions are alternated — which is what probing does — rather than when
    one direction is repeated, where the blur appearing and disappearing
    cancels out.
    """
    env = NoisyEnvironment()
    learner = ControlLearner()
    frame = env.reset()
    previous = frame.frame[0]
    for action in (GameAction.ACTION2, GameAction.ACTION4) * 8:
        if action.value not in frame.available_actions:
            continue
        frame = env.step(action)
        learner.observe(previous, frame.frame[0], action)
        previous = frame.frame[0]

    down = learner.mapping().get(GameAction.ACTION2)
    assert down is not None
    assert down[1] != 0, f"expected sideways drift on a vertical move, got {down}"


def test_the_learning_policies_do_not_survive_the_noise():
    """A negative result, measured: see docs/noise-validation.md.

    Both policies clear every level on the quiet mock and neither finishes here.
    This is the honest state of the work, and the test exists so that a future
    change which fixes it fails loudly rather than passing unnoticed.
    """
    for agent in (ExplorerAgent(), NavigatorAgent()):
        result = run_episode(agent, NoisyEnvironment(), max_actions=400)
        assert not result.won, f"{agent.name} now survives the noise — update the docs"


def test_the_same_policies_do_clear_the_quiet_mock():
    """The contrast that makes the previous test mean something."""
    for agent in (ExplorerAgent(), NavigatorAgent()):
        assert run_episode(agent, MockEnvironment(), max_actions=400).won


def test_the_overlap_estimator_rescues_the_policy_on_this_mock():
    """And yet it is not the default — see docs/estimator-comparison.md.

    On this mock the overlap estimator recovers the controls exactly and the
    policy clears every level, where the centroid reports diagonals and it
    clears none. On recorded real boards the ranking reverses, 55% against 79%,
    so the default follows the real data. This test records that the mock
    result is genuine, not that the estimator is better.
    """
    import arcagi3.navigator as navigator_module
    from arcagi3.control import ControlLearner

    agent = NavigatorAgent()
    agent.control = ControlLearner(estimator="overlap")
    original = navigator_module.ControlLearner
    navigator_module.ControlLearner = lambda: ControlLearner(estimator="overlap")
    try:
        result = run_episode(agent, NoisyEnvironment(), max_actions=400)
    finally:
        navigator_module.ControlLearner = original
    assert result.won
