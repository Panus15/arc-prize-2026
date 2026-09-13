"""Tests for the segmentation layer."""

from __future__ import annotations

import pytest

from arcagi3.perception import Node, background_colour, segment

# A ring of 3s with a single 5 sitting inside its hole.
RING_WITH_CORE = [
    [0, 0, 0, 0, 0],
    [0, 3, 3, 3, 0],
    [0, 3, 5, 3, 0],
    [0, 3, 3, 3, 0],
    [0, 0, 0, 0, 0],
]


def test_background_is_the_largest_area_not_necessarily_zero():
    grid = [[7, 7, 7], [7, 2, 7], [7, 7, 7]]
    assert background_colour(grid) == 7


def test_background_ties_break_deterministically():
    grid = [[1, 2], [2, 1]]
    assert background_colour(grid) == 1
    assert background_colour(grid) == 1


def test_segments_are_four_connected_not_eight():
    """Diagonal touching must not merge two objects."""
    grid = [[4, 0], [0, 4]]
    seg = segment(grid, background=0)
    assert len(seg.nodes) == 2


def test_node_ids_run_top_left_first():
    grid = [[0, 2], [3, 0]]
    seg = segment(grid, background=0)
    assert seg.nodes[0].colour == 2  # row 0 comes before row 1
    assert seg.nodes[1].colour == 3


def test_enclosed_object_is_recorded_as_a_child():
    seg = segment(RING_WITH_CORE)
    ring = next(n for n in seg.nodes if n.colour == 3)
    core = next(n for n in seg.nodes if n.colour == 5)
    assert core.id in ring.children


def test_an_object_beside_another_is_not_its_child():
    grid = [[0, 0, 0, 0], [0, 3, 0, 5], [0, 0, 0, 0]]
    seg = segment(grid, background=0)
    assert all(node.children == () for node in seg.nodes)


def test_adjacency_links_objects_sharing_an_edge():
    grid = [[1, 2]]
    seg = segment(grid, background=0)
    assert seg.adjacency == ((0, 1),)
    assert seg.neighbours_of(0) == (1,)


def test_objects_that_only_touch_diagonally_are_not_adjacent():
    grid = [[1, 0], [0, 2]]
    seg = segment(grid, background=0)
    assert seg.adjacency == ()


def test_hash_ignores_position():
    """The property that makes an object trackable between frames."""
    left = segment([[4, 4, 0, 0]], background=0).nodes[0]
    right = segment([[0, 0, 4, 4]], background=0).nodes[0]
    assert left.hash == right.hash


def test_hash_separates_different_colours_and_shapes():
    a = segment([[4, 4]], background=0).nodes[0]
    b = segment([[5, 5]], background=0).nodes[0]
    c = segment([[4, 4, 4]], background=0).nodes[0]
    assert a.hash != b.hash
    assert a.hash != c.hash


def test_hash_is_stable_across_calls():
    first = segment([[6, 0, 6]], background=0).nodes[0].hash
    second = segment([[6, 0, 6]], background=0).nodes[0].hash
    assert first == second


def test_duplicates_groups_identical_objects():
    grid = [[4, 0, 4], [0, 0, 0], [4, 0, 0]]
    seg = segment(grid, background=0)
    dupes = seg.duplicates()
    assert len(dupes) == 1
    assert len(next(iter(dupes.values()))) == 3


def test_bbox_shape_and_pixels():
    node = segment([[0, 0, 0], [0, 7, 7], [0, 7, 0]], background=0).nodes[0]
    assert node.pixels == 3
    assert node.bbox == (1, 1, 2, 2)
    assert node.shape == (2, 2)
    assert node.top_left == (1, 1)


def test_of_colour_filters():
    seg = segment(RING_WITH_CORE)
    assert len(seg.of_colour(3)) == 1
    assert len(seg.of_colour(9)) == 0


def test_background_only_board_has_no_objects():
    seg = segment([[0, 0], [0, 0]])
    assert seg.nodes == ()
    assert seg.adjacency == ()


def test_rejects_empty_and_ragged_grids():
    with pytest.raises(ValueError, match="empty"):
        segment([])
    with pytest.raises(ValueError, match="ragged"):
        segment([[1, 2], [3]])


def test_scales_to_a_full_size_board():
    """64x64 is the real board size; segmentation must stay quick on it."""
    grid = [[(r // 2 + c // 2) % 4 for c in range(64)] for r in range(64)]
    seg = segment(grid)
    assert seg.shape == (64, 64)
    assert seg.nodes


def test_node_is_hashable_and_frozen():
    node = segment([[1]], background=0).nodes[0]
    assert isinstance(node, Node)
    with pytest.raises(AttributeError):
        node.colour = 9  # type: ignore[misc]


def test_nested_containment_survives_the_bbox_pruning():
    """A ring inside a ring: the optimisation must not lose the outer link."""
    grid = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 2, 0, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]
    seg = segment(grid)
    outer = next(n for n in seg.nodes if n.colour == 1)
    inner = next(n for n in seg.nodes if n.colour == 2)
    assert inner.id in outer.children


def test_an_open_shape_encloses_nothing():
    """A C-shape has a gap, so what sits in its mouth is not contained."""
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 1, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ]
    grid[2][2] = 2
    seg = segment(grid)
    c_shape = next(n for n in seg.nodes if n.colour == 1)
    assert c_shape.children == ()


def test_segmentation_of_a_busy_full_size_board_is_quick():
    """Guards the containment optimisation: this board has ~200 objects.

    The naive version flooded the whole board once per node and took most of a
    second here, which at ~150 actions per trial is minutes of pure perception.
    """
    import time

    grid = [[0] * 64 for _ in range(64)]
    for r in range(0, 64, 3):
        for c in range(0, 64, 3):
            grid[r][c] = (r + c) % 9 + 1

    started = time.perf_counter()
    seg = segment(grid)
    elapsed = time.perf_counter() - started

    assert len(seg.nodes) > 150
    assert elapsed < 0.2, f"segmentation took {elapsed:.3f}s on a busy board"
