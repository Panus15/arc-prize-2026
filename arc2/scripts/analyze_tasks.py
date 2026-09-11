"""Measured statistical profile of the ARC-AGI-2 public corpus.

Every number in `docs/dataset-analysis.md` is produced by this script; nothing
there is estimated. Run it from the workspace directory:

    python scripts/analyze_tasks.py                 # both splits + comparison
    python scripts/analyze_tasks.py --split evaluation
    python scripts/analyze_tasks.py --json out.json

The pass is deterministic: no sampling, no shuffling, no bootstrap. Uncertainty
on a proportion is reported as a Wilson score interval, which is a closed form.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

# Running this file directly puts scripts/ on sys.path, not the workspace root,
# so `import arc` has to be pointed at the package next to this directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from arc.dataset import (  # noqa: E402  (must follow the sys.path bootstrap above)
    SPLITS,
    DatasetNotFoundError,
    Grid,
    Task,
    TaskFormatError,
    data_root,
    load_split,
)

# Two-sided 95% normal quantile, used by the Wilson interval below.
Z95 = 1.959963984540054

# Pair-level shape relations, in the order they are reported.
SHAPE_RELATIONS = ("same", "output_multiple", "input_multiple", "other")

# The dihedral group of the square: the eight rigid re-labellings of a grid.
D4_NAMES = (
    "identity",
    "rot90",
    "rot180",
    "rot270",
    "flip_lr",
    "flip_ud",
    "transpose",
    "anti_transpose",
)

# Trivial pair relations whose task-level ceiling is worth counting.
TRIVIAL_NAMES = (*D4_NAMES, "tile", "upscale", "downscale", "crop")


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #


def _array(grid: Grid) -> np.ndarray:
    return np.array(grid, dtype=np.int16)


def _eq(a: np.ndarray, b: np.ndarray) -> bool:
    """Exact grid equality — dimensions included, as the competition scores it."""
    return a.shape == b.shape and bool(np.array_equal(a, b))


def _d4(arr: np.ndarray) -> dict[str, np.ndarray]:
    """The eight dihedral images of `arr`, keyed by D4_NAMES."""
    return {
        "identity": arr,
        "rot90": np.rot90(arr, 1),
        "rot180": np.rot90(arr, 2),
        "rot270": np.rot90(arr, 3),
        "flip_lr": np.fliplr(arr),
        "flip_ud": np.flipud(arr),
        "transpose": arr.T,
        "anti_transpose": np.rot90(arr, 2).T,
    }


def _summary(values: Sequence[int]) -> dict[str, float]:
    """n / min / quartiles / max / mean. Quartiles use numpy linear interpolation."""
    arr = np.asarray(values, dtype=float)
    q1, median, q3 = (float(x) for x in np.percentile(arr, [25, 50, 75]))
    return {
        "n": len(values),
        "min": float(arr.min()),
        "q1": q1,
        "median": median,
        "q3": q3,
        "max": float(arr.max()),
        "mean": round(float(arr.mean()), 3),
    }


def _wilson(successes: int, total: int) -> tuple[float, float]:
    """95% Wilson score interval for `successes`/`total`, as fractions."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1.0 + Z95**2 / total
    centre = (p + Z95**2 / (2 * total)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / total + Z95**2 / (4 * total**2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _pct(successes: int, total: int) -> float:
    return 0.0 if total == 0 else round(100.0 * successes / total, 2)


def _counts(counter: Counter[int]) -> dict[str, int]:
    """Counter over ints -> JSON-safe dict, ordered by key."""
    return {str(key): int(counter[key]) for key in sorted(counter)}


def _rate(successes: int, total: int, unit: str) -> dict[str, Any]:
    """A proportion carried with its denominator, so the comparison can test it."""
    low, high = _wilson(successes, total)
    return {
        "k": int(successes),
        "n": int(total),
        "pct": _pct(successes, total),
        "ci95": [round(100 * low, 2), round(100 * high, 2)],
        "unit": unit,
    }


# --------------------------------------------------------------------------- #
# grid-level measures
# --------------------------------------------------------------------------- #


def background_symbol(arr: np.ndarray) -> int:
    """Most frequent symbol in `arr`; ties break to the lowest symbol id.

    ARC has no declared background, so the modal symbol is the only definition
    that can be computed rather than assumed.
    """
    counts = np.bincount(arr.reshape(-1), minlength=10)
    return int(np.argmax(counts))


def symmetries(arr: np.ndarray) -> dict[str, bool]:
    """Which reflections/rotations map `arr` onto itself (transpose: square only)."""
    square = arr.shape[0] == arr.shape[1]
    return {
        "flip_lr": _eq(arr, np.fliplr(arr)),
        "flip_ud": _eq(arr, np.flipud(arr)),
        "rot180": _eq(arr, np.rot90(arr, 2)),
        "transpose": square and _eq(arr, arr.T),
    }


def _find(parent: list[int], node: int) -> int:
    root = node
    while parent[root] != root:
        root = parent[root]
    while parent[node] != root:
        parent[node], node = root, parent[node]
    return root


def component_count(arr: np.ndarray, background: int) -> int:
    """Number of 4-connected same-colour regions, treating `background` as empty.

    Counted as (foreground cells - successful unions) so the whole grid is one
    numpy pass plus a union-find over adjacent same-colour pairs only.
    """
    mask = arr != background
    foreground = int(mask.sum())
    if foreground == 0:
        return 0

    index = np.arange(arr.size).reshape(arr.shape)
    right = mask[:, :-1] & mask[:, 1:] & (arr[:, :-1] == arr[:, 1:])
    down = mask[:-1, :] & mask[1:, :] & (arr[:-1, :] == arr[1:, :])
    heads = np.concatenate((index[:, :-1][right], index[:-1, :][down])).tolist()
    tails = np.concatenate((index[:, 1:][right], index[1:, :][down])).tolist()

    parent = list(range(arr.size))
    merges = 0
    for head, tail in zip(heads, tails, strict=True):
        root_a, root_b = _find(parent, head), _find(parent, tail)
        if root_a != root_b:
            parent[root_a] = root_b
            merges += 1
    return foreground - merges


# --------------------------------------------------------------------------- #
# pair-level measures
# --------------------------------------------------------------------------- #


def shape_relation(inp: np.ndarray, out: np.ndarray) -> str:
    """One of SHAPE_RELATIONS for a single input/output pair."""
    ih, iw = inp.shape
    oh, ow = out.shape
    if (ih, iw) == (oh, ow):
        return "same"
    if oh % ih == 0 and ow % iw == 0:
        return "output_multiple"
    if ih % oh == 0 and iw % ow == 0:
        return "input_multiple"
    return "other"


def _block_factors(small: np.ndarray, big: np.ndarray) -> tuple[int, int] | None:
    """(k, m) with big.shape == (k*h, m*w), or None when it is not a clean multiple."""
    sh, sw = small.shape
    bh, bw = big.shape
    if bh % sh or bw % sw:
        return None
    factors = (bh // sh, bw // sw)
    return None if factors == (1, 1) else factors


def is_tiling(inp: np.ndarray, out: np.ndarray) -> bool:
    """Output is the input repeated k x m times, every tile identical to the input."""
    factors = _block_factors(inp, out)
    return factors is not None and _eq(np.tile(inp, factors), out)


def is_d4_tiling(inp: np.ndarray, out: np.ndarray) -> bool:
    """Looser tiling: each tile is *some* dihedral image of the input."""
    factors = _block_factors(inp, out)
    if factors is None:
        return False
    rows, cols = factors
    ih, iw = inp.shape
    variants = [v for v in _d4(inp).values() if v.shape == inp.shape]
    for r in range(rows):
        for c in range(cols):
            block = out[r * ih : (r + 1) * ih, c * iw : (c + 1) * iw]
            if not any(_eq(block, v) for v in variants):
                return False
    return True


def is_upscale(small: np.ndarray, big: np.ndarray) -> bool:
    """`big` is `small` with every cell blown up into a k x m block."""
    factors = _block_factors(small, big)
    if factors is None:
        return False
    rows, cols = factors
    return _eq(np.repeat(np.repeat(small, rows, axis=0), cols, axis=1), big)


def is_crop(inp: np.ndarray, out: np.ndarray) -> bool:
    """Output is a contiguous sub-rectangle of the input, strictly smaller."""
    ih, iw = inp.shape
    oh, ow = out.shape
    if oh > ih or ow > iw or (oh, ow) == (ih, iw):
        return False
    for r in range(ih - oh + 1):
        for c in range(iw - ow + 1):
            if np.array_equal(inp[r : r + oh, c : c + ow], out):
                return True
    return False


def trivial_relations(inp: np.ndarray, out: np.ndarray) -> dict[str, bool]:
    """Which trivial rules turn this input into this output."""
    found = {name: _eq(image, out) for name, image in _d4(inp).items()}
    found["tile"] = is_tiling(inp, out)
    found["tile_d4"] = is_d4_tiling(inp, out)
    found["upscale"] = is_upscale(inp, out)
    found["downscale"] = is_upscale(out, inp)
    found["crop"] = is_crop(inp, out)
    return found


def _rule_holds(name: str, inp: np.ndarray, out: np.ndarray) -> bool:
    """Task-level rule check, reusing the pair-level definitions."""
    if name in D4_NAMES:
        return _eq(_d4(inp)[name], out)
    if name == "tile":
        return is_tiling(inp, out)
    if name == "upscale":
        return is_upscale(inp, out)
    if name == "downscale":
        return is_upscale(out, inp)
    return is_crop(inp, out)


def _scale_factors(name: str, inp: np.ndarray, out: np.ndarray) -> tuple[int, int] | None:
    if name in ("tile", "upscale"):
        return _block_factors(inp, out)
    if name == "downscale":
        return _block_factors(out, inp)
    return None


def task_trivial_rules(pairs: Sequence[tuple[np.ndarray, np.ndarray]]) -> set[str]:
    """Rules that hold for *every* pair of a task — the ceiling of a trivial solver.

    A scaling rule additionally has to use the same factors throughout, since a
    solver must infer one factor pair from the demonstrations.
    """
    holding: set[str] = set()
    for name in TRIVIAL_NAMES:
        factors = {_scale_factors(name, inp, out) for inp, out in pairs}
        if len(factors) != 1:
            continue
        if all(_rule_holds(name, inp, out) for inp, out in pairs):
            holding.add(name)
    return holding


# --------------------------------------------------------------------------- #
# split analysis
# --------------------------------------------------------------------------- #


def _pair_arrays(task: Task) -> list[tuple[np.ndarray, np.ndarray]]:
    """Input/output array pairs of a task, skipping pairs with a held-out output."""
    out: list[tuple[np.ndarray, np.ndarray]] = []
    for pair in task.pairs:
        if pair.output is not None:
            out.append((_array(pair.input), _array(pair.output)))
    return out


def _grid_stats(arrays: Sequence[np.ndarray]) -> dict[str, Any]:
    """Size, palette, background, symmetry and object counts over a set of grids."""
    heights = [int(a.shape[0]) for a in arrays]
    widths = [int(a.shape[1]) for a in arrays]
    cells = [int(a.size) for a in arrays]
    palette = [int(np.unique(a).size) for a in arrays]

    backgrounds = Counter(background_symbol(a) for a in arrays)
    non_zero_bg = sum(v for k, v in backgrounds.items() if k != 0)
    without_zero = sum(1 for a in arrays if not bool((a == 0).any()))

    sym = Counter()
    squares = 0
    for a in arrays:
        flags = symmetries(a)
        squares += int(a.shape[0] == a.shape[1])
        for name, hit in flags.items():
            sym[name] += int(hit)
        if flags["flip_lr"] or flags["flip_ud"] or flags["rot180"] or flags["transpose"]:
            sym["any"] += 1

    objects = [component_count(a, background_symbol(a)) for a in arrays]
    objects_zero_bg = [component_count(a, 0) for a in arrays]

    return {
        "grids": len(arrays),
        "height": _summary(heights),
        "width": _summary(widths),
        "cells": _summary(cells),
        "palette_size": _summary(palette),
        "palette_size_counts": _counts(Counter(palette)),
        "background_symbol_counts": _counts(backgrounds),
        "background_not_zero": _rate(non_zero_bg, len(arrays), "grid"),
        "grids_without_symbol_zero": _rate(without_zero, len(arrays), "grid"),
        "square_grids": _rate(squares, len(arrays), "grid"),
        "symmetry": {
            "flip_lr": _rate(sym["flip_lr"], len(arrays), "grid"),
            "flip_ud": _rate(sym["flip_ud"], len(arrays), "grid"),
            "rot180": _rate(sym["rot180"], len(arrays), "grid"),
            "transpose_of_square": _rate(sym["transpose"], squares, "grid"),
            "any": _rate(sym["any"], len(arrays), "grid"),
        },
        "objects_modal_background": _summary(objects),
        "objects_symbol_zero_background": _summary(objects_zero_bg),
    }


def _colour_stats(
    tasks: Sequence[Task], pairs: Sequence[tuple[np.ndarray, np.ndarray]]
) -> dict[str, Any]:
    """Palette relationships between inputs and outputs."""
    subset = 0
    introduced_pairs = 0
    dropped_pairs = 0
    introduced_symbols: Counter[int] = Counter()
    introduced_per_pair: Counter[int] = Counter()
    same_palette = 0

    for inp, out in pairs:
        in_set = set(np.unique(inp).tolist())
        out_set = set(np.unique(out).tolist())
        new = out_set - in_set
        gone = in_set - out_set
        subset += int(not new)
        same_palette += int(in_set == out_set)
        introduced_pairs += int(bool(new))
        dropped_pairs += int(bool(gone))
        introduced_per_pair[len(new)] += 1
        introduced_symbols.update(new)

    task_palettes: list[int] = []
    task_backgrounds: Counter[int] = Counter()
    for task in tasks:
        symbols: set[int] = set()
        counts = np.zeros(10, dtype=np.int64)
        for pair in task.pairs:
            for grid in (pair.input, pair.output):
                if grid is None:
                    continue
                arr = _array(grid)
                symbols.update(np.unique(arr).tolist())
                counts += np.bincount(arr.reshape(-1), minlength=10)
        task_palettes.append(len(symbols))
        task_backgrounds[int(np.argmax(counts))] += 1

    total = len(pairs)
    return {
        "output_palette_subset_of_input": _rate(subset, total, "pair"),
        "output_palette_equals_input": _rate(same_palette, total, "pair"),
        "output_introduces_new_symbol": _rate(introduced_pairs, total, "pair"),
        "output_drops_input_symbol": _rate(dropped_pairs, total, "pair"),
        "new_symbols_per_pair_counts": _counts(introduced_per_pair),
        "introduced_symbol_counts": _counts(introduced_symbols),
        "task_palette_size": _summary(task_palettes),
        "task_palette_size_counts": _counts(Counter(task_palettes)),
        "task_background_symbol_counts": _counts(task_backgrounds),
        "task_background_not_zero": _rate(
            sum(v for k, v in task_backgrounds.items() if k != 0), len(tasks), "task"
        ),
    }


def _shape_stats(
    tasks: Sequence[Task], pairs: Sequence[tuple[np.ndarray, np.ndarray]]
) -> dict[str, Any]:
    """Pair-level shape relations plus the task-level shape rules."""
    relations = Counter(shape_relation(inp, out) for inp, out in pairs)

    fixed_output = 0
    fixed_output_varying_input = 0
    same_shape_tasks = 0
    constant_ratio_tasks = 0
    for task in tasks:
        arrays = _pair_arrays(task)
        out_shapes = {out.shape for _, out in arrays}
        in_shapes = {inp.shape for inp, _ in arrays}
        if all(inp.shape == out.shape for inp, out in arrays):
            same_shape_tasks += 1
        if len(out_shapes) == 1:
            fixed_output += 1
            if len(in_shapes) > 1:
                fixed_output_varying_input += 1
        ratios = {(out.shape[0] / inp.shape[0], out.shape[1] / inp.shape[1]) for inp, out in arrays}
        if len(ratios) == 1 and next(iter(ratios)) != (1.0, 1.0):
            constant_ratio_tasks += 1

    return {
        "pair_relations": {
            name: _rate(relations[name], len(pairs), "pair") for name in SHAPE_RELATIONS
        },
        "tasks_all_pairs_same_shape": _rate(same_shape_tasks, len(tasks), "task"),
        "tasks_fixed_output_shape": _rate(fixed_output, len(tasks), "task"),
        "tasks_fixed_output_shape_varying_input": _rate(
            fixed_output_varying_input, len(tasks), "task"
        ),
        "tasks_constant_size_ratio": _rate(constant_ratio_tasks, len(tasks), "task"),
    }


def _trivial_stats(
    tasks: Sequence[Task], pairs: Sequence[tuple[np.ndarray, np.ndarray]]
) -> dict[str, Any]:
    """How far a transformation-free baseline could possibly get."""
    hits: Counter[str] = Counter()
    any_trivial = 0
    tiny_outputs = 0
    for inp, out in pairs:
        found = trivial_relations(inp, out)
        for name, hit in found.items():
            hits[name] += int(hit)
        core = [found[name] for name in (*D4_NAMES, "tile", "upscale")]
        any_trivial += int(any(core))
        tiny_outputs += int(out.size <= 4)

    task_hits: Counter[str] = Counter()
    solvable_by_any_rule = 0
    constant_output_tasks = 0
    for task in tasks:
        arrays = _pair_arrays(task)
        rules = task_trivial_rules(arrays)
        for name in rules:
            task_hits[name] += 1
        # `crop` alone is not a program: it says a crop exists, not which one.
        if rules - {"crop"}:
            solvable_by_any_rule += 1
        first = arrays[0][1]
        if all(_eq(first, out) for _, out in arrays):
            constant_output_tasks += 1

    total_pairs, total_tasks = len(pairs), len(tasks)
    return {
        "pairs": {
            name: _rate(hits[name], total_pairs, "pair") for name in (*TRIVIAL_NAMES, "tile_d4")
        },
        "pairs_any_trivial": _rate(any_trivial, total_pairs, "pair"),
        "pairs_with_output_up_to_4_cells": _rate(tiny_outputs, total_pairs, "pair"),
        "tasks_every_pair": {
            name: _rate(task_hits[name], total_tasks, "task") for name in TRIVIAL_NAMES
        },
        "tasks_solvable_by_one_trivial_rule": _rate(solvable_by_any_rule, total_tasks, "task"),
        "tasks_constant_output": _rate(constant_output_tasks, total_tasks, "task"),
    }


def analyse_split(split: str) -> dict[str, Any]:
    """Full measured profile of one split."""
    tasks = load_split(split)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    inputs: list[np.ndarray] = []
    outputs: list[np.ndarray] = []
    held_out = 0

    for task in tasks:
        for pair in task.pairs:
            arr_in = _array(pair.input)
            inputs.append(arr_in)
            if pair.output is None:
                held_out += 1
                continue
            arr_out = _array(pair.output)
            outputs.append(arr_out)
            pairs.append((arr_in, arr_out))

    train_counts = Counter(len(t.train) for t in tasks)
    test_counts = Counter(len(t.test) for t in tasks)

    result: dict[str, Any] = {
        "split": split,
        "tasks": len(tasks),
        "pairs": sum(len(t.pairs) for t in tasks),
        "pairs_with_output": len(pairs),
        "pairs_without_output": held_out,
        "grids": len(inputs) + len(outputs),
        "task_shape": {
            "train_pairs_counts": _counts(train_counts),
            "train_pairs": _summary([len(t.train) for t in tasks]),
            "test_inputs_counts": _counts(test_counts),
            "test_inputs": _summary([len(t.test) for t in tasks]),
            # Scoring is all-or-nothing per task, so extra test inputs are extra risk.
            "tasks_with_multiple_test_inputs": _rate(
                sum(v for k, v in test_counts.items() if k > 1), len(tasks), "task"
            ),
        },
        "inputs": _grid_stats(inputs),
        "outputs": _grid_stats(outputs),
        "shapes": _shape_stats(tasks, pairs),
        "colours": _colour_stats(tasks, pairs),
        "trivial": _trivial_stats(tasks, pairs),
    }
    result["headline"] = _headline(result)
    return result


def _headline(res: dict[str, Any]) -> dict[str, Any]:
    """The measures the training-vs-evaluation comparison walks over."""
    return {
        "rates": {
            "pairs same input/output shape": res["shapes"]["pair_relations"]["same"],
            "pairs output is a multiple": res["shapes"]["pair_relations"]["output_multiple"],
            "pairs input is a multiple": res["shapes"]["pair_relations"]["input_multiple"],
            "pairs shape relation 'other'": res["shapes"]["pair_relations"]["other"],
            "tasks all pairs same shape": res["shapes"]["tasks_all_pairs_same_shape"],
            "tasks fixed output shape": res["shapes"]["tasks_fixed_output_shape"],
            "pairs output palette subset of input": res["colours"][
                "output_palette_subset_of_input"
            ],
            "pairs output introduces a new symbol": res["colours"]["output_introduces_new_symbol"],
            "tasks background is not symbol 0": res["colours"]["task_background_not_zero"],
            "input grids background is not 0": res["inputs"]["background_not_zero"],
            "pairs output == input (identity)": res["trivial"]["pairs"]["identity"],
            "pairs any trivial relation": res["trivial"]["pairs_any_trivial"],
            "tasks one trivial rule fits all pairs": res["trivial"][
                "tasks_solvable_by_one_trivial_rule"
            ],
            "input grids with any symmetry": res["inputs"]["symmetry"]["any"],
            "output grids with any symmetry": res["outputs"]["symmetry"]["any"],
            "tasks with more than one test input": res["task_shape"][
                "tasks_with_multiple_test_inputs"
            ],
        },
        "values": {
            "median input cells": res["inputs"]["cells"]["median"],
            "median output cells": res["outputs"]["cells"]["median"],
            "mean input cells": res["inputs"]["cells"]["mean"],
            "median input palette size": res["inputs"]["palette_size"]["median"],
            "mean input palette size": res["inputs"]["palette_size"]["mean"],
            "mean task palette size": res["colours"]["task_palette_size"]["mean"],
            "median objects per input grid": res["inputs"]["objects_modal_background"]["median"],
            "mean objects per input grid": res["inputs"]["objects_modal_background"]["mean"],
            "mean objects per output grid": res["outputs"]["objects_modal_background"]["mean"],
            "mean train pairs per task": res["task_shape"]["train_pairs"]["mean"],
            "mean test inputs per task": res["task_shape"]["test_inputs"]["mean"],
        },
    }


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    """Difference of every headline measure, with Wilson intervals on proportions."""
    rates = []
    for name, l_rate in left["headline"]["rates"].items():
        r_rate = right["headline"]["rates"][name]
        overlap = l_rate["ci95"][0] <= r_rate["ci95"][1] and r_rate["ci95"][0] <= l_rate["ci95"][1]
        rates.append(
            {
                "measure": name,
                "unit": l_rate["unit"],
                left["split"]: l_rate,
                right["split"]: r_rate,
                "diff_pct_points": round(r_rate["pct"] - l_rate["pct"], 2),
                "ci95_overlap": overlap,
            }
        )

    values = [
        {
            "measure": name,
            left["split"]: value,
            right["split"]: right["headline"]["values"][name],
            "diff": round(right["headline"]["values"][name] - value, 3),
        }
        for name, value in left["headline"]["values"].items()
    ]
    return {"splits": [left["split"], right["split"]], "rates": rates, "values": values}


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #


def _rate_line(label: str, rate: dict[str, Any], width: int = 42) -> str:
    return (
        f"  {label:<{width}} {rate['k']:>6} / {rate['n']:<6} "
        f"{rate['pct']:>6.2f}%  [{rate['ci95'][0]:.2f}, {rate['ci95'][1]:.2f}]"
    )


def _summary_line(label: str, s: dict[str, float], width: int = 24) -> str:
    return (
        f"  {label:<{width}} n={s['n']:<6} min {s['min']:>5.0f}  q1 {s['q1']:>6.1f}  "
        f"median {s['median']:>6.1f}  q3 {s['q3']:>6.1f}  max {s['max']:>5.0f}  "
        f"mean {s['mean']:>7.2f}"
    )


def _print_grid_block(title: str, stats: dict[str, Any]) -> None:
    print(f"\n  {title} ({stats['grids']} grids)")
    for key, label in (
        ("height", "height (rows)"),
        ("width", "width (cols)"),
        ("cells", "cells"),
        ("palette_size", "palette size"),
        ("objects_modal_background", "objects (modal bg)"),
        ("objects_symbol_zero_background", "objects (bg = 0)"),
    ):
        print(_summary_line(label, stats[key]))


def print_split_report(res: dict[str, Any]) -> None:
    """Human-readable report for one split."""
    split = res["split"]
    print(
        f"\n{'=' * 78}\n[{split}] {res['tasks']} tasks, {res['pairs']} pairs, "
        f"{res['grids']} grids ({res['pairs_with_output']} pairs carry an output)"
    )
    print("=" * 78)

    print("\n-- 1. shape relations (per pair with output) --")
    for name in SHAPE_RELATIONS:
        print(_rate_line(name, res["shapes"]["pair_relations"][name]))
    for key, label in (
        ("tasks_all_pairs_same_shape", "tasks: every pair keeps the shape"),
        ("tasks_fixed_output_shape", "tasks: one output shape for all pairs"),
        ("tasks_fixed_output_shape_varying_input", "  ... while input shapes vary"),
        ("tasks_constant_size_ratio", "tasks: constant size ratio (not 1:1)"),
    ):
        print(_rate_line(label, res["shapes"][key]))

    print("\n-- 1b + 5. grid size, palette size and object counts --")
    _print_grid_block("input grids", res["inputs"])
    _print_grid_block("output grids", res["outputs"])

    print("\n-- 2. colour usage --")
    print(f"  input background symbol counts   {res['inputs']['background_symbol_counts']}")
    print(f"  task background symbol counts    {res['colours']['task_background_symbol_counts']}")
    for label, rate in (
        ("input grids: background is not 0", res["inputs"]["background_not_zero"]),
        ("output grids: background is not 0", res["outputs"]["background_not_zero"]),
        ("tasks: background is not 0", res["colours"]["task_background_not_zero"]),
        ("input grids: symbol 0 absent", res["inputs"]["grids_without_symbol_zero"]),
        ("pairs: output palette subset of input", res["colours"]["output_palette_subset_of_input"]),
        ("pairs: output palette equals input", res["colours"]["output_palette_equals_input"]),
        ("pairs: output introduces a new symbol", res["colours"]["output_introduces_new_symbol"]),
        ("pairs: output drops an input symbol", res["colours"]["output_drops_input_symbol"]),
    ):
        print(_rate_line(label, rate))
    print(f"  new symbols per pair             {res['colours']['new_symbols_per_pair_counts']}")
    print(f"  symbols introduced (by symbol)   {res['colours']['introduced_symbol_counts']}")
    print(_summary_line("palette per task", res["colours"]["task_palette_size"]))
    print(f"  palette size per task            {res['colours']['task_palette_size_counts']}")

    print("\n-- 3. trivial relations --")
    print("  per pair:")
    for name in (*TRIVIAL_NAMES, "tile_d4"):
        print(_rate_line(name, res["trivial"]["pairs"][name]))
    print(_rate_line("ANY of identity/D4/tile/upscale", res["trivial"]["pairs_any_trivial"]))
    print(
        _rate_line("outputs of at most 4 cells", res["trivial"]["pairs_with_output_up_to_4_cells"])
    )
    print("  per task (rule holds for every pair, same factors):")
    for name in TRIVIAL_NAMES:
        print(_rate_line(name, res["trivial"]["tasks_every_pair"][name]))
    print(
        _rate_line(
            "ANY single trivial rule (crop excluded)",
            res["trivial"]["tasks_solvable_by_one_trivial_rule"],
        )
    )
    print(
        _rate_line(
            "all outputs identical (constant output)", res["trivial"]["tasks_constant_output"]
        )
    )

    print("\n-- 4. symmetry --")
    for label, stats in (("input grids", res["inputs"]), ("output grids", res["outputs"])):
        print(f"  {label}:")
        print(_rate_line("square", stats["square_grids"]))
        for name in ("flip_lr", "flip_ud", "rot180", "transpose_of_square", "any"):
            print(_rate_line(name, stats["symmetry"][name]))

    print("\n-- 6. task shape --")
    print(f"  train pairs per task   {res['task_shape']['train_pairs_counts']}")
    print(_summary_line("train pairs", res["task_shape"]["train_pairs"]))
    print(f"  test inputs per task   {res['task_shape']['test_inputs_counts']}")
    print(_summary_line("test inputs", res["task_shape"]["test_inputs"]))
    print(
        _rate_line(
            "tasks needing >1 correct output",
            res["task_shape"]["tasks_with_multiple_test_inputs"],
        )
    )


def print_comparison(cmp: dict[str, Any]) -> None:
    """Side-by-side of every headline measure."""
    left, right = cmp["splits"]
    print(f"\n{'=' * 78}\n-- 7. {left} vs {right} --\n{'=' * 78}")
    print(f"\n  {'measure':<40} {'unit':<5} {left:>10} {right:>10} {'diff':>8}  CI95 overlap")
    for row in cmp["rates"]:
        print(
            f"  {row['measure']:<40} {row['unit']:<5} {row[left]['pct']:>9.2f}% "
            f"{row[right]['pct']:>9.2f}% {row['diff_pct_points']:>+8.2f}  "
            f"{'yes' if row['ci95_overlap'] else 'NO'}"
        )
    print(f"\n  {'measure':<40} {'':<5} {left:>10} {right:>10} {'diff':>8}")
    for row in cmp["values"]:
        print(
            f"  {row['measure']:<40} {'':<5} {row[left]:>10.3f} {row[right]:>10.3f} "
            f"{row['diff']:>+8.3f}"
        )
    print(
        "\n  CI95 = Wilson score interval on the proportion in each split.\n"
        "  'yes' means the two intervals overlap: with 120 evaluation tasks the\n"
        "  difference is not separable from sampling noise. Pair- and grid-level\n"
        "  intervals are optimistic, since grids inside one task are not independent."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="analyze_tasks.py",
        description="Measured statistical profile of the ARC-AGI-2 public corpus",
    )
    parser.add_argument("--split", choices=SPLITS, help="only this split (default: both)")
    parser.add_argument("--json", metavar="OUT", help="also write the full result as JSON")
    args = parser.parse_args(argv)

    splits = [args.split] if args.split else list(SPLITS)
    try:
        print(f"dataset: {data_root()}")
        results = {split: analyse_split(split) for split in splits}
    except (DatasetNotFoundError, TaskFormatError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for split in splits:
        print_split_report(results[split])

    payload: dict[str, Any] = {"dataset": str(data_root()), "splits": results}
    if len(splits) == 2:
        payload["comparison"] = compare(results[splits[0]], results[splits[1]])
        print_comparison(payload["comparison"])

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2, sort_keys=False), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
