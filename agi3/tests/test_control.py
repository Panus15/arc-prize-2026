"""Tests for centroid-based control learning.

The method exists because object-hash matching collapsed on real boards, so the
cases that matter here are the noisy ones: a sprite that changes shape while it
moves, and scenery that moves on every action regardless of which.
"""

from __future__ import annotations

from arcengine import GameAction

from arcagi3.control import (
    ControlLearner,
    colour_centroids,
    direction_of,
)

PLAYER = 4
HUD = 7
BOARD = 8


def board(
    player: tuple[int, int], hud_row: int | None = None, player_cells: int = 1
) -> list[list[int]]:
    grid = [[0] * BOARD for _ in range(BOARD)]
    for offset in range(player_cells):
        r, c = player[0], player[1] + offset
        if 0 <= r < BOARD and 0 <= c < BOARD:
            grid[r][c] = PLAYER
    if hud_row is not None:
        for c in range(BOARD):
            grid[hud_row][c] = HUD
    return grid


# --- primitives ------------------------------------------------------------


def test_centroids_report_position_and_size():
    grid = [[0, 0], [0, 5]]
    found = colour_centroids(grid)
    assert found[5] == (1.0, 1.0, 1)
    assert found[0][2] == 3


def test_direction_reduces_a_shift_to_a_grid_step():
    assert direction_of((0.0, 1.4)) == (0, 1)
    assert direction_of((-2.0, 0.0)) == (-1, 0)


def test_tiny_shifts_count_as_no_movement():
    """A sprite changing shape in place nudges its centroid; that is not a move."""
    assert direction_of((0.01, -0.01)) == (0, 0)


# --- learning --------------------------------------------------------------


def test_learns_a_direction_per_action():
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    assert learner.mapping()[GameAction.ACTION4] == (0, 1)
    assert learner.mapping()[GameAction.ACTION2] == (1, 0)
    assert learner.controlled_colour() == PLAYER


def test_ignores_scenery_that_moves_on_every_action():
    """A timer bar ticks whichever button is pressed, so it is not the player."""
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c), hud_row=0), board((2, c + 1), hud_row=1), GameAction.ACTION4)
        learner.observe(board((4, c), hud_row=0), board((5, c), hud_row=1), GameAction.ACTION2)
    assert learner.controlled_colour() == PLAYER


def test_survives_a_sprite_that_changes_shape_while_moving():
    """The failure that killed object-hash matching on real boards."""
    learner = ControlLearner()
    for c in range(4):
        before = board((2, c), player_cells=1)
        after = board((2, c + 1), player_cells=2)  # sprite "animates"
        learner.observe(before, after, GameAction.ACTION4)
        learner.observe(
            board((4, c), player_cells=2), board((5, c), player_cells=1), GameAction.ACTION2
        )
    assert learner.mapping().get(GameAction.ACTION4) == (0, 1)


def test_large_regions_are_treated_as_scenery():
    """Background fills more than a tenth of the board and must not be a candidate."""
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    assert learner.controlled_colour() != 0


def test_nothing_is_claimed_before_enough_observations():
    learner = ControlLearner()
    learner.observe(board((2, 0)), board((2, 1)), GameAction.ACTION4)
    assert learner.mapping() == {}
    assert learner.confidence() == 0.0


def test_a_single_action_is_not_enough_to_claim_control():
    """One direction could be a drifting object; control means several."""
    learner = ControlLearner()
    for c in range(5):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
    assert learner.mapping() == {}


def test_confidence_is_high_when_an_action_always_does_the_same_thing():
    learner = ControlLearner()
    for c in range(5):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    assert learner.confidence() > 0.9


def test_confidence_drops_when_an_action_is_inconsistent():
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    # Same button, contradictory outcomes.
    for c in range(4):
        learner.observe(board((2, c + 1)), board((2, c)), GameAction.ACTION4)
    assert learner.confidence() < 0.9


def test_action_for_inverts_the_mapping():
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    assert learner.action_for((0, 1)) is GameAction.ACTION4
    assert learner.action_for((-1, 0)) is None


def test_summary_says_so_when_nothing_was_learned():
    assert "no control found" in ControlLearner().summary()


def test_summary_names_the_colour_and_the_moves():
    learner = ControlLearner()
    for c in range(4):
        learner.observe(board((2, c)), board((2, c + 1)), GameAction.ACTION4)
        learner.observe(board((4, c)), board((5, c)), GameAction.ACTION2)
    text = learner.summary()
    assert f"colour {PLAYER}" in text
    assert "RIGHT" in text and "DOWN" in text


def test_empty_boards_are_ignored_rather_than_crashing():
    learner = ControlLearner()
    learner.observe([], [], GameAction.ACTION1)
    assert learner.samples == 0
