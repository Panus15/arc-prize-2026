"""Tests for the noise wrapper, and for which noise actually matters."""

from __future__ import annotations

from arcengine import GameAction

from arcagi3.budget import run_episode
from arcagi3.click_mock import ClickEnvironment
from arcagi3.clicker import ClickAgent
from arcagi3.mock import MockEnvironment
from arcagi3.navigator import NavigatorAgent
from arcagi3.noise import HUD_COLOUR, NoiseWrapper

PLAYER = 4
GOAL = 2


def test_it_wraps_a_walking_environment():
    frame = NoiseWrapper(MockEnvironment()).reset()
    assert frame.frame[-1]


def test_it_wraps_a_clicking_environment_too():
    """The point of a wrapper: it is not tied to one game."""
    frame = NoiseWrapper(ClickEnvironment()).reset()
    assert frame.frame[-1]


def test_unknown_attributes_pass_through_to_the_wrapped_environment():
    wrapped = NoiseWrapper(MockEnvironment())
    assert wrapped.optimal_actions == MockEnvironment().optimal_actions


def test_the_hud_advances_even_on_a_refused_action():
    wrapped = NoiseWrapper(MockEnvironment())
    wrapped.reset()
    first = wrapped.step(GameAction.ACTION1).frame[-1][-1]  # up, off the board
    second = wrapped.step(GameAction.ACTION1).frame[-1][-1]
    assert first != second
    assert HUD_COLOUR in first


def test_the_sprite_changes_size_between_frames():
    wrapped = NoiseWrapper(MockEnvironment(), sprite_colour=PLAYER)
    wrapped.reset()
    sizes = set()
    for _ in range(4):
        frame = wrapped.step(GameAction.ACTION2)
        sizes.add(sum(row.count(PLAYER) for row in frame.frame[-1]))
    assert len(sizes) > 1


def test_both_kinds_of_noise_can_be_switched_off():
    plain = MockEnvironment().reset().frame[0]
    quiet = NoiseWrapper(MockEnvironment(), hud=False, animate=False).reset().frame[-1]
    assert len(quiet) == len(plain)


# --- which noise actually matters ------------------------------------------


def walk(**noise) -> bool:
    return run_episode(
        NavigatorAgent(), NoiseWrapper(MockEnvironment(), **noise), max_actions=400
    ).won


def test_animating_the_controlled_object_defeats_the_policy():
    """The narrow thing that breaks control learning."""
    assert not walk(sprite_colour=PLAYER)


def test_it_still_defeats_the_policy_without_the_hud():
    """So the HUD is not what does the damage."""
    assert not walk(sprite_colour=PLAYER, hud=False)


def test_animating_only_the_goal_costs_nothing():
    assert walk(sprite_colour=GOAL)


def test_the_hud_alone_costs_nothing():
    assert walk(animate=False)


def test_animating_everything_is_easier_than_animating_the_player_alone():
    """Measured, and counter-intuitive: more noise is not harder here.

    What defeats control learning is noise on the signal being learned from,
    not noise in general.
    """
    assert walk()
    assert not walk(sprite_colour=PLAYER)


def test_the_click_policy_survives_this_wrapper():
    result = run_episode(ClickAgent(), NoiseWrapper(ClickEnvironment()), max_actions=100)
    assert result.won
