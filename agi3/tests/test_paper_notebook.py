"""The paper's public notebook must be what paper/build_notebook.py builds.

It is committed with its outputs so readers see results without running it, and
it bundles copies of our modules, so it can fall behind the code silently. The
sources of its cells are compared, not the outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PAPER = Path(__file__).resolve().parents[2] / "paper"
sys.path.insert(0, str(PAPER))

import build_notebook  # noqa: E402

COMMITTED = PAPER / "notebook.ipynb"


def sources(notebook: dict) -> list[str]:
    return ["".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            for cell in notebook["cells"]]


def test_the_committed_notebook_matches_its_builder():
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert sources(committed) == sources(build_notebook.build()), (
        "paper/notebook.ipynb is stale - run: python paper/build_notebook.py --run"
    )


def test_it_was_executed_and_no_cell_failed():
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    code = [c for c in committed["cells"] if c["cell_type"] == "code"]
    assert all(c.get("execution_count") for c in code)
    assert not [c for c in code if any(o.get("output_type") == "error" for o in c.get("outputs", []))]


def test_the_live_tables_show_what_the_documents_say():
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    printed = "\n".join(
        "".join(o.get("text", "")) for c in committed["cells"] for o in c.get("outputs", [])
    )
    assert "navigator        yes             WIN 3/3            lost 0/3" in printed  # gap table
    assert "animate the controlled object only       clears 0 of 3" in printed  # ablation
    assert "animate only the goal                    clears 3 of 3" in printed


def test_nothing_local_leaks_in():
    text = COMMITTED.read_text(encoding="utf-8")
    assert "/home/" not in text and "/root/" not in text
