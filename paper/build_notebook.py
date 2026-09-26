"""Build the paper's public notebook: self-contained, and every table computed live.

    python paper/build_notebook.py          # writes paper/notebook.ipynb (no outputs)
    python paper/build_notebook.py --run    # ...and executes it, keeping the outputs

The notebook carries the `arcagi3` modules it needs and the two measured-result
files as %%writefile cells, so it runs on Kaggle with nothing attached but the
competition (for the offline `arc-agi` wheels), or anywhere with `pip install
arc-agi`. Tables that come from simulation are recomputed when it runs; only the
figures measured on recorded real games (2.8 GB of traces) are shipped as data.

tests/test_paper_notebook.py fails if the committed notebook's cells drift from
what this script builds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from textwrap import dedent

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "agi3" / "scripts"))

from build_kaggle_notebook import (  # noqa: E402
    PACKAGE,
    code,
    markdown,
    package_closure,
    writefile,
)

OUT = HERE / "notebook.ipynb"
DATA = HERE / "data"
PKG = "/tmp/arcagi_pkg/arcagi3"
DATA_TMP = "/tmp/paper_data"
ROOTS = ("agent", "budget", "explorer", "mock", "navigator_v1", "noisy_mock", "click_mock",
         "noise", "router")
WHEELS = "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels"


def md(text: str) -> dict:
    return markdown(dedent(text).strip())


def py(text: str) -> dict:
    return code(dedent(text).strip())


def cells() -> list[dict]:
    modules = package_closure(ROOTS)
    out = [
        md("""
        # What a program-only agent can establish about an unknown environment

        Companion notebook to our ARC Prize 2026 Paper Track writeup.

        It runs offline and needs nothing attached but the competition itself. Every
        table that comes from simulation is **computed when you run it**; the figures
        measured against 500 recorded real games are shipped as two small JSON files,
        because the recordings are 2.8&nbsp;GB. Each number traces to a document in the
        repository (github.com/Panus15/arc-prize-2026, MIT-0) recording the run behind
        it, including the numbers that contradict our earlier claims.
        """),
        md("""
        ## Setup

        The competition's `arc-agi` package supplies the frame and action types; on
        Kaggle it installs from the competition's offline wheels. Our library and the
        measured results follow as generated cells — scroll past them to section 1.
        """),
        py(f"""
        import importlib.util
        import os
        import pathlib
        import subprocess
        import sys

        if importlib.util.find_spec("arcengine") is None:
            wheels = pathlib.Path("{WHEELS}")
            source = ["--no-index", "--find-links", str(wheels)] if wheels.is_dir() else []
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", *source, "arc-agi"],
                           check=True)
        for folder in ("{PKG}", "{DATA_TMP}"):
            os.makedirs(folder, exist_ok=True)
        print("arc-agi available:", importlib.util.find_spec("arcengine") is not None)
        """),
        writefile(f"{PKG}/__init__.py", '"""arcagi3, bundled into the paper notebook."""'),
    ]
    for name in modules:
        out.append(writefile(f"{PKG}/{name}.py", (PACKAGE / f"{name}.py").read_text()))
    for data in sorted(DATA.glob("*.json")):
        out.append(writefile(f"{DATA_TMP}/{data.name}", data.read_text().rstrip("\n")))
    out += [
        py(f"""
        import json

        sys.path.insert(0, str(pathlib.Path("{PKG}").parent))
        DATA = pathlib.Path("{DATA_TMP}")
        print("library: {len(modules)} modules · data:", sorted(p.name for p in DATA.iterdir()))
        """),
        md("""
        ## 1. Simulation does not predict reality

        Two arenas, the same policies. One is the quiet environment we wrote first; the
        other carries noise measured from recorded games — a HUD strip that advances on
        every action, sprites that change shape as they move, and as a consequence a
        board that changes on essentially every action. This is the walking policy as it
        stood when these measurements were made (`navigator_v1`, frozen at commit
        `dc949b4`).
        """),
        py("""
        from arcagi3.agent import GreedyAgent, RandomAgent
        from arcagi3.budget import run_episode
        from arcagi3.explorer import ExplorerAgent
        from arcagi3.mock import MockEnvironment
        from arcagi3.navigator_v1 import NavigatorAgent as FrozenNavigator
        from arcagi3.noisy_mock import NoisyEnvironment

        POLICIES = {
            "random": lambda: RandomAgent(seed=0),
            "greedy": GreedyAgent,
            "explorer": ExplorerAgent,
            "navigator": FrozenNavigator,
        }
        ARENAS = {"quiet mock": MockEnvironment, "noise-calibrated": NoisyEnvironment}


        def outcome(policy, arena):
            r = run_episode(policy(), arena(), max_actions=400)
            return f"{'WIN' if r.won else 'lost'} {r.levels_completed}/{r.total_levels}"


        print(f"{'policy':<11}{'learns?':>9}" + "".join(f"{name:>20}" for name in ARENAS))
        print("-" * 60)
        for name, policy in POLICIES.items():
            learns = "no" if name in ("random", "greedy") else "yes"
            print(f"{name:<11}{learns:>9}" + "".join(f"{outcome(policy, a):>20}" for a in ARENAS.values()))
        """),
        md("""
        The noise destroys **only the methods that learn**: the random and hard-coded
        policies score identically in both arenas, holding no model for the noise to
        corrupt. On a board carrying the noise real boards carry, **random play beats
        both of our deliberate policies**. And the quiet arena carries **no
        information** about the noisy one: three policies clear every level there, then
        their fates diverge completely.
        """),
        md("""
        ## 2. What probing costs, measured on real boards

        From replaying 500 recorded runs — 25 official games, 20 passes each — and
        checking the mapping the learner recovers against the action labels the
        recordings carry.
        """),
        py("""
        measured = json.loads((DATA / "control-learning-measured.json").read_text())
        curve = measured["learning_curve"]
        print(measured["_provenance"]["source"], "\\n")
        print(f"{'observations':>13}{'mappings':>10}{'correct':>9}{'accuracy':>10}")
        print("-" * 42)
        for row in curve:
            print(f"{row['observations']:>13}{row['mappings']:>10}{row['correct']:>9}"
                  f"{row['accuracy']:>9.0%}")
        """),
        py("""
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([r["observations"] for r in curve], [r["accuracy"] * 100 for r in curve],
                marker="o", color="#2b6cb0")
        ax.set_xscale("log")
        ax.set_xlabel("observations fed to the learner (log scale)")
        ax.set_ylabel("mapping accuracy (%)")
        ax.set_title("Learning the controls: accuracy against evidence")
        ax.grid(alpha=0.3)
        ax.set_ylim(0, 100)
        plt.tight_layout()
        plt.show()
        """),
        md("""
        Nothing is learnable below about ten observations; accuracy climbs to roughly
        80% by eighty, then flattens. A separate measurement matters more in play: a
        mapping *correct about two directions* costs a median of **12 observations**.
        Those answer different questions, and conflating them — as we did — makes
        starting look far more expensive than it is.
        """),
        md("""
        ## 3. Is the learner's confidence honest?

        It reports a confidence alongside each mapping. If that number means anything,
        accuracy should rise with it.
        """),
        py("""
        bands = measured["confidence_calibration"]
        print(f"{'confidence':>14}{'mappings':>10}{'correct':>9}{'accuracy':>10}")
        print("-" * 43)
        for row in bands:
            label = f"{row['confidence_from']:.1f}-{row['confidence_to']:.1f}"
            print(f"{label:>14}{row['mappings']:>10}{row['correct']:>9}{row['accuracy']:>9.0%}")

        fig, ax = plt.subplots(figsize=(7, 4))
        labels = [f"{r['confidence_from']:.1f}-{r['confidence_to']:.1f}" for r in bands]
        ax.bar(labels, [r["accuracy"] * 100 for r in bands], color="#2b6cb0")
        ax.set_xlabel("reported confidence")
        ax.set_ylabel("observed accuracy (%)")
        ax.set_title("Confidence is informative, with a cliff at 0.6")
        ax.set_ylim(0, 100)
        ax.grid(axis="y", alpha=0.3)
        plt.tight_layout()
        plt.show()
        """),
        md("""
        A sharp threshold at **0.6**: below it the mapping is 36% accurate, above it
        84–85%. Waiting for higher confidence buys no further accuracy while costing
        actions — and even the top band is wrong 15% of the time.
        """),
        md("""
        ## 4. Five times the simulator convinced us

        | # | Looked settled | Then failed | Mechanism |
        |---|---|---|---|
        | 1 | object matching, 88% in our mock | **0.4%** on 2,276 real transitions | an animating sprite does not match itself between frames |
        | 2 | "the board changed" as a click signal | **worthless** — 91–100% of real clicks change the board | a signal present almost always separates nothing |
        | 3 | our best walking policy, 3/3 levels | **0/3** once the board is noisy | the centre of mass is dragged sideways by animation |
        | 4 | cell alignment, 3/3 on the *calibrated* mock | **55%** on real boards, against the centroid's 79% | alignment discards an observation whenever nothing lines up |
        | 5 | the walker, 3/3 on our mock | pressed ACTION5 on **97–100%** of turns in all 8 real walking games offering it | our mock offered interaction only on the goal; the real engine fixes the action list for a whole game |

        The fourth passed an arena calibrated from 500 real runs and still selected the
        worse design: matching measured statistics is not sufficient, because the
        statistics one chooses to match come from the same understanding that shaped the
        method. The fifth was found by replaying recorded real boards through the agent
        we were about to submit — the first of our three checks, again.
        """),
        md("""
        ## 5. The fifth, reproduced

        `static_actions=True` makes our mock behave like the real engine: the same
        actions on every frame. The frozen walker against the one we submit:
        """),
        py("""
        from arcengine import GameAction

        from arcagi3.router import walker as submitted_walker

        SCRAMBLED = {GameAction.ACTION1: (0, 1), GameAction.ACTION2: (0, -1),
                     GameAction.ACTION3: (1, 0), GameAction.ACTION4: (-1, 0)}
        STATIC_ARENAS = {
            "quiet, list varies (our mock)": lambda: MockEnvironment(),
            "quiet, fixed list (engine)": lambda: MockEnvironment(static_actions=True),
            "noisy, fixed list": lambda: NoisyEnvironment(static_actions=True),
            "noisy, fixed, scrambled": lambda: NoisyEnvironment(moves=SCRAMBLED, static_actions=True),
        }
        WALKERS = {"frozen (dc949b4)": FrozenNavigator, "submitted": submitted_walker}

        print(f"{'arena':<32}" + "".join(f"{name:>20}" for name in WALKERS))
        print("-" * 72)
        for arena, make in STATIC_ARENAS.items():
            print(f"{arena:<32}" + "".join(f"{outcome(w, make):>20}" for w in WALKERS.values()))
        """),
        md("""
        The frozen walker wins only the environment we wrote first. These are still
        mocks: they show the mechanism was found and repaired, not that real levels are
        now cleared — that is what the live run is for.
        """),
        md("""
        ## 6. Which noise actually matters

        Each property switched on separately, against our walking game, with the frozen
        walker the ablation was measured on:
        """),
        py("""
        from arcagi3.noise import NoiseWrapper

        PLAYER, GOAL = 4, 2
        ABLATION = {
            "animate the controlled object only": dict(sprite_colour=PLAYER),
            "animate every small object": dict(),
            "animate only the goal": dict(sprite_colour=GOAL),
            "HUD alone, nothing animated": dict(animate=False),
            "controlled object, no HUD": dict(sprite_colour=PLAYER, hud=False),
        }
        for label, noise in ABLATION.items():
            r = run_episode(FrozenNavigator(), NoiseWrapper(MockEnvironment(), **noise), max_actions=400)
            print(f"{label:<40} clears {r.levels_completed} of {r.total_levels}")
        """),
        md("""
        More noise made the test **easier**. It is not noise that defeats learning, but
        noise on the signal being learned from — a statement about learning agents
        rather than about ARC.
        """),
        md("""
        ## 7. Three checks

        These would have caught all five of our failures, and need no ARC-specific
        knowledge:

        1. **Test against data you did not generate.** Recordings, traces, a live game.
        2. **Measure the base rate of whatever signal you learn from.** A signal present
           95% of the time separates nothing, however reasonable it looks.
        3. **Measure component accuracy and playing ability separately.** Ours diverged
           completely: 79% mapping accuracy, zero levels cleared.

        The noise is packaged as a wrapper that takes any environment returning
        `FrameData`, so the same check runs against another team's agent unchanged:
        """),
        py("""
        from arcagi3.click_mock import ClickEnvironment

        frame = NoiseWrapper(ClickEnvironment()).reset()
        print(f"wrapped a game it was not written for: board is "
              f"{len(frame.frame[-1])}x{len(frame.frame[-1][0])}")
        """),
        md("""
        ## Reproducing all of it

        ```bash
        git clone https://github.com/Panus15/arc-prize-2026
        cd arc-prize-2026/agi3 && ./setup.sh
        .venv/bin/pytest                                          # the test suite
        PYTHONPATH=. .venv/bin/python scripts/simulation_gap.py   # section 1
        PYTHONPATH=. .venv/bin/python scripts/validate_control.py # sections 2 and 3
        PYTHONPATH=. .venv/bin/python scripts/replay_traces.py    # failure 5, on real boards
        PYTHONPATH=. .venv/bin/python scripts/static_arenas.py    # section 5, all arenas
        ```
        """),
    ]
    for index, cell in enumerate(out):
        cell["id"] = f"cell-{index:02d}"
    return out


def build() -> dict:
    return {
        "cells": cells(),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true", help="execute it and keep the outputs")
    args = parser.parse_args(argv)

    import nbformat

    # Through the JSON text, so sources become the strings nbclient expects.
    notebook = nbformat.reads(json.dumps(build()), as_version=4)
    nbformat.validate(notebook)
    if args.run:
        from nbclient import NotebookClient

        NotebookClient(notebook, timeout=900, kernel_name="python3",
                       resources={"metadata": {"path": "/tmp"}}).execute()
    nbformat.write(notebook, str(OUT))
    print(f"wrote {OUT} ({len(notebook.cells)} cells{', executed' if args.run else ''})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
