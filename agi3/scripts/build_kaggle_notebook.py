"""Build the ARC-AGI-3 Kaggle submission notebook from this repository.

    python scripts/build_kaggle_notebook.py                     # placeholder username
    python scripts/build_kaggle_notebook.py --username YOURNAME

Writes submission/kaggle/submission.ipynb and kernel-metadata.json. The notebook
is committed, so it can be uploaded through the Kaggle website with no local
Python at all; tests/test_kaggle_notebook.py fails if it falls out of date.

Kaggle runs a submission notebook twice. On "Save & Run All" there is no game
server — the official pattern just writes a placeholder submission. This one
also plays a small synthetic game through Kaggle's own copy of the runner, so
anything broken fails the save instead of spending one of the five daily
submissions. On the competition rerun it plays the hidden games for real.

The pattern (wheel install, runner copy, slim registry, gateway .env) follows
the official ARC-AGI-3-Kaggle-Starter. Internet is off in both runs, so our
package travels inside the notebook as %%writefile cells.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from textwrap import dedent

AGI3 = Path(__file__).resolve().parents[1]
PACKAGE = AGI3 / "arcagi3"
AGENT = AGI3 / "submission" / "my_agent.py"
FIXTURE = AGI3 / "tests" / "fixtures" / "environment_files" / "tw01" / "00000001"
OUT = AGI3 / "submission" / "kaggle"

COMP = "/kaggle/input/competitions/arc-prize-2026-arc-agi-3"
PKG_TMP = "/tmp/arcagi_pkg/arcagi3"
ROOTS = ("router", "sdk_adapter")
PLACEHOLDER = "REPLACE_WITH_YOUR_KAGGLE_USERNAME"


def package_closure(roots: tuple[str, ...] = ROOTS) -> list[str]:
    """Modules of `arcagi3` that the submitted agent imports, transitively."""
    seen: set[str] = set()
    todo = list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        tree = ast.parse((PACKAGE / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                parts = node.module.split(".")
                if parts[0] == "arcagi3" and len(parts) > 1:
                    todo.append(parts[1])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    parts = alias.name.split(".")
                    if parts[0] == "arcagi3" and len(parts) > 1:
                        todo.append(parts[1])
    return sorted(seen)


def lines(text: str) -> list[str]:
    """nbformat's list-of-lines form: every line but the last keeps its newline."""
    out = text.splitlines(keepends=True)
    if out and out[-1].endswith("\n"):
        out[-1] = out[-1][:-1]
    return out


def code(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [],
            "source": lines(source)}


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": lines(source)}


def writefile(path: str, body: str) -> dict:
    return code(f"%%writefile {path}\n{body}")


PREPARE = dedent(
    f'''\
    import os
    import shutil
    import subprocess
    import sys

    RERUN = bool(os.getenv("KAGGLE_IS_COMPETITION_RERUN"))
    SOURCE = "{COMP}/ARC-AGI-3-Agents"
    # On the rerun the runner lives where Kaggle's sample puts it. On save it is
    # built under /tmp so nothing lands in /kaggle/working as a stray output.
    RUNNER = "/kaggle/working/ARC-AGI-3-Agents" if RERUN else "/tmp/ARC-AGI-3-Agents"

    if not os.path.isdir(SOURCE):
        raise SystemExit(f"runner not found at {{SOURCE}} - is the competition attached as input?")
    shutil.rmtree(RUNNER, ignore_errors=True)
    shutil.copytree(SOURCE, RUNNER)
    shutil.copytree("{PKG_TMP}", os.path.join(RUNNER, "arcagi3"))
    shutil.copy("/tmp/my_agent.py", os.path.join(RUNNER, "agents", "templates", "my_agent.py"))

    # The runner's registry imports LLM templates whose dependencies are not
    # installed; replace it, as Kaggle's own sample does, keeping only ours.
    with open(os.path.join(RUNNER, "agents", "__init__.py"), "w") as f:
        f.write(
            "from typing import Type\\n"
            "from dotenv import load_dotenv\\n"
            "from .agent import Agent, Playback\\n"
            "from .swarm import Swarm\\n"
            "from .templates.random_agent import Random\\n"
            "from .templates.my_agent import MyAgent\\n"
            "load_dotenv()\\n"
            "AVAILABLE_AGENTS: dict[str, Type[Agent]] = {{'random': Random, 'myagent': MyAgent}}\\n"
        )
    print("runner prepared at", RUNNER, "| competition rerun:", RERUN)
    '''
)

SELF_CHECK = dedent(
    '''\
    # Save & Run All: play the synthetic fixture through Kaggle's runner copy.
    # A failure here stops the save, before a daily submission is spent.
    if not RERUN:
        check = """
    import inspect
    import logging
    from agents import AVAILABLE_AGENTS
    from agents.agent import Agent
    from agents.templates.my_agent import MyAgent
    # What the rerun's `main.py --agent myagent` will look up.
    assert AVAILABLE_AGENTS.get("myagent") is MyAgent, "myagent is not registered"
    if "arc_env" not in inspect.signature(Agent.__init__).parameters:
        # A runner older than the one this was tested against cannot host an
        # offline game; failing here would block a submission that may be fine.
        print("runner predates offline play: checked import and registration only")
        print("SELF-CHECK PASSED (import only)")
    else:
        from arc_agi import Arcade, OperationMode
        arc = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir="/tmp/fixture_envs",
                     recordings_dir="/tmp/fixture_rec", logger=logging.getLogger("check"))
        card = arc.open_scorecard(tags=["self-check"])
        agent = MyAgent(card_id=card, game_id="tw01", agent_name="self-check",
                        ROOT_URL="http://localhost", record=False,
                        arc_env=arc.make("tw01", scorecard_id=card), tags=["self-check"])
        agent.MAX_ACTIONS = 60
        agent.main()
        final = agent.frames[-1]
        print("self-check:", final.state.name, final.levels_completed, "/", final.win_levels,
              "in", agent.action_counter, "actions")
        assert final.levels_completed == final.win_levels == 2, "agent failed the fixture"
        print("SELF-CHECK PASSED")
    """
        result = subprocess.run([sys.executable, "-c", check], cwd=RUNNER,
                                capture_output=True, text=True)
        print(result.stdout[-3000:])
        if result.returncode != 0:
            print(result.stderr[-3000:])
            raise SystemExit("self-check failed - do not submit this version")
    '''
)

RERUN_CELL = dedent(
    '''\
    if RERUN:
        # Wait for the gateway sidecar, point the runner at it, and play.
        !curl --fail --retry 999 --retry-all-errors --retry-delay 5 --retry-max-time 600 http://gateway:8001/api/games
        with open(os.path.join(RUNNER, ".env"), "w") as f:
            f.write(
                "SCHEME=http\\nHOST=gateway\\nPORT=8001\\nARC_API_KEY=test-key-123\\n"
                "ARC_BASE_URL=http://gateway:8001/\\nOPERATION_MODE=online\\n"
                "ENVIRONMENTS_DIR=\\nRECORDINGS_DIR=/kaggle/working/server_recording\\n"
            )
        !cd {RUNNER} && MPLBACKEND=agg python main.py --agent myagent
    '''
)

PLACEHOLDER_SUBMISSION = dedent(
    '''\
    if not RERUN:
        # Save & Run All needs a submission file to exist; the real one is
        # written by the gateway during the competition rerun.
        import pandas as pd
        pd.DataFrame(
            data=[["1_0", "1", True, 1]],
            columns=["row_id", "game_id", "end_of_game", "score"],
        ).to_parquet("/kaggle/working/submission.parquet", index=False)
        print("placeholder submission.parquet written")
    '''
)


def build() -> dict:
    modules = package_closure()
    cells = [
        markdown(
            "# ARC Prize 2026 · ARC-AGI-3 submission\n\n"
            "A program-only agent: no neural network, no GPU. It walks games that offer "
            "directions and clicks games that only take the mouse.\n\n"
            "Source, tests and the Paper Track writeup: "
            "https://github.com/Panus15/arc-prize-2026 (MIT-0).\n\n"
            "**Generated** by `agi3/scripts/build_kaggle_notebook.py` - edit the repository, "
            "not these cells."
        ),
        code(
            f"!pip install --no-index --find-links {COMP}/arc_agi_3_wheels arc-agi python-dotenv"
        ),
        # %%writefile does not create directories.
        code(
            "import os\n\n"
            f"for d in ({PKG_TMP!r}, '/tmp/fixture_envs/tw01/00000001'):\n"
            "    os.makedirs(d, exist_ok=True)"
        ),
        markdown(f"## Our package (`arcagi3`, {len(modules)} modules)"),
        # %%writefile refuses an empty body, so the package marker carries a docstring.
        writefile(f"{PKG_TMP}/__init__.py", (PACKAGE / "__init__.py").read_text().strip()
                  or '"""arcagi3, bundled into the submission notebook."""'),
    ]
    for name in modules:
        cells.append(writefile(f"{PKG_TMP}/{name}.py", (PACKAGE / f"{name}.py").read_text()))
    cells += [
        markdown("## The agent the runner plays"),
        writefile("/tmp/my_agent.py", AGENT.read_text()),
        markdown("## Self-check fixture (a synthetic two-level game, not a real one)"),
        writefile("/tmp/fixture_envs/tw01/00000001/tw01.py", (FIXTURE / "tw01.py").read_text()),
        writefile(
            "/tmp/fixture_envs/tw01/00000001/metadata.json",
            (FIXTURE / "metadata.json").read_text(),
        ),
        markdown("## Prepare the runner, check, then play"),
        code(PREPARE),
        code(SELF_CHECK),
        code(RERUN_CELL),
        code(PLACEHOLDER_SUBMISSION),
    ]
    for index, cell in enumerate(cells):
        cell["id"] = f"cell-{index:02d}"
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "kaggle": {
                "accelerator": "none",
                "isInternetEnabled": False,
                "isGpuEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def metadata(username: str) -> dict:
    return {
        "id": f"{username}/arc-prize-2026-arc-agi-3-program-agent",
        "title": "ARC Prize 2026 - ARC-AGI-3 program-only agent",
        "code_file": "submission.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "dataset_sources": [],
        "kernel_sources": [],
        "competition_sources": ["arc-prize-2026-arc-agi-3"],
        "model_sources": [],
    }


def render(notebook: dict) -> str:
    return json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--username", default=PLACEHOLDER)
    args = parser.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    notebook = build()
    import nbformat  # validated here so a malformed notebook never reaches Kaggle

    nbformat.validate(nbformat.from_dict(notebook))
    (OUT / "submission.ipynb").write_text(render(notebook), encoding="utf-8")
    (OUT / "kernel-metadata.json").write_text(
        json.dumps(metadata(args.username), indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {OUT / 'submission.ipynb'} ({len(notebook['cells'])} cells, "
          f"{len(package_closure())} package modules)")
    if args.username == PLACEHOLDER:
        print("kernel-metadata.json carries a placeholder username (only needed for the CLI route)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
