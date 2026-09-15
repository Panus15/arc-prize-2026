"""Tests for shortest-path routing and learned obstacles."""

from __future__ import annotations

from arcagi3.navigation import ObstacleModel, find_path

WALLED = [
    [0, 0, 0, 0, 0],
    [0, 8, 8, 8, 0],
    [0, 0, 0, 0, 0],
]


def blocking(*colours: int) -> ObstacleModel:
    model = ObstacleModel()
    for colour in colours:
        model.record_blocked(colour)
    return model


# --- the obstacle model ----------------------------------------------------


def test_a_refused_move_marks_the_colour_blocked():
    model = ObstacleModel()
    model.record_blocked(8)
    assert model.is_blocked(8)


def test_moving_through_a_colour_clears_it():
    model = blocking(8)
    model.record_passable(8)
    assert not model.is_blocked(8)


def test_passing_through_outranks_a_later_refusal():
    """A cell can refuse entry for reasons unrelated to its colour."""
    model = ObstacleModel()
    model.record_passable(3)
    model.record_blocked(3)
    assert not model.is_blocked(3)


def test_unseen_colours_are_assumed_passable():
    assert not ObstacleModel().is_blocked(5)


def test_summary_lists_both_sides():
    model = ObstacleModel()
    model.record_blocked(8)
    model.record_passable(0)
    assert "blocked: 8" in model.summary()
    assert "passable: 0" in model.summary()


# --- routing ---------------------------------------------------------------


def test_routes_straight_when_nothing_is_in_the_way():
    assert find_path([[0, 0, 0]], (0, 0), (0, 2)) == [(0, 1), (0, 1)]


def test_routes_around_a_known_wall():
    path = find_path(WALLED, (0, 1), (2, 1), blocking(8))
    assert path is not None
    assert len(path) == 4  # the detour, not the blocked two-step
    assert (1, 0) in path


def test_walks_through_a_wall_it_has_not_learned_about():
    """Without evidence the colour blocks, the short way is the right guess."""
    assert find_path(WALLED, (0, 1), (2, 1)) == [(1, 0), (1, 0)]


def test_returns_none_when_the_goal_is_walled_off():
    grid = [[0, 8, 0]]
    assert find_path(grid, (0, 0), (0, 2), blocking(8)) is None


def test_the_goal_cell_itself_is_always_enterable():
    """The goal is usually the object being walked to, so it cannot be a wall."""
    grid = [[0, 0, 8]]
    assert find_path(grid, (0, 0), (0, 2), blocking(8)) == [(0, 1), (0, 1)]


def test_no_steps_needed_when_already_there():
    assert find_path([[0]], (0, 0), (0, 0)) == []


def test_off_board_requests_are_refused():
    assert find_path([[0]], (0, 0), (5, 5)) is None
    assert find_path([[0]], (-1, 0), (0, 0)) is None


def test_empty_grid_is_refused():
    assert find_path([], (0, 0), (0, 0)) is None


def test_path_is_a_shortest_one():
    grid = [[0] * 6 for _ in range(6)]
    path = find_path(grid, (0, 0), (5, 5))
    assert path is not None
    assert len(path) == 10


def test_routing_scales_to_a_full_size_board():
    grid = [[0] * 64 for _ in range(64)]
    path = find_path(grid, (0, 0), (63, 63))
    assert path is not None
    assert len(path) == 126
