"""The committed Kaggle notebook must be exactly what the sources build.

It is committed so it can be uploaded through the Kaggle website with no local
Python, which means it can silently fall behind the code it bundles. These
tests make that a failure instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AGI3 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AGI3 / "scripts"))

import build_kaggle_notebook as builder  # noqa: E402

COMMITTED = AGI3 / "submission" / "kaggle" / "submission.ipynb"


def test_committed_notebook_is_up_to_date():
    fresh = builder.render(builder.build())
    assert COMMITTED.read_text(encoding="utf-8") == fresh, (
        "submission/kaggle/submission.ipynb is stale - run scripts/build_kaggle_notebook.py"
    )


def test_every_module_the_agent_imports_is_bundled():
    bundled = set(builder.package_closure())
    assert {"router", "sdk_adapter", "navigator", "clicker"} <= bundled
    source = COMMITTED.read_text(encoding="utf-8")
    for name in bundled:
        assert f"%%writefile {builder.PKG_TMP}/{name}.py" in source


def test_no_writefile_cell_is_empty():
    """%%writefile refuses an empty body; this failed once in emulation."""
    notebook = json.loads(COMMITTED.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        text = "".join(cell["source"])
        if text.startswith("%%writefile"):
            assert text.split("\n", 1)[1].strip(), text.splitlines()[0]


def test_directories_are_created_before_files_are_written():
    """%%writefile does not create folders; this failed once in emulation too."""
    notebook = json.loads(COMMITTED.read_text(encoding="utf-8"))
    sources = ["".join(cell["source"]) for cell in notebook["cells"]]
    first_write = next(i for i, s in enumerate(sources) if s.startswith("%%writefile"))
    assert any("os.makedirs" in s for s in sources[:first_write])


def test_internet_is_off_and_no_gpu_is_requested():
    notebook = json.loads(COMMITTED.read_text(encoding="utf-8"))
    kaggle = notebook["metadata"]["kaggle"]
    assert kaggle["isInternetEnabled"] is False
    assert kaggle["isGpuEnabled"] is False
    meta = json.loads((COMMITTED.parent / "kernel-metadata.json").read_text())
    assert meta["enable_internet"] is False
    assert meta["competition_sources"] == ["arc-prize-2026-arc-agi-3"]


def test_nothing_local_leaks_into_the_notebook():
    source = COMMITTED.read_text(encoding="utf-8")
    assert "/home/" not in source
    assert "/root/" not in source
    # The only key the notebook may carry is the gateway's fixed test key.
    for line in source.splitlines():
        if "ARC_API_KEY=" in line:
            assert "ARC_API_KEY=test-key-123" in line
