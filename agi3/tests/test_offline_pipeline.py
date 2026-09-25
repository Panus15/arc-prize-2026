"""End to end: real engine, real runner loop, our submitted agent — no network.

A synthetic game in the exact on-disk format the SDK downloads is loaded by
`Arcade` in OFFLINE mode and played through the official runner's `Agent.main`,
using the same `submission/my_agent.py` that goes into the Kaggle notebook.
Nothing about agent quality is measured here; the game is a fixture. What is
checked is that every joint between the pieces holds.

Skipped unless the runner has been fetched with scripts/vendor_framework.sh.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

AGI3 = Path(__file__).resolve().parents[1]
FIXTURES = AGI3 / "tests" / "fixtures" / "environment_files"
RUNNER = AGI3 / "vendor" / "ARC-AGI-3-Agents"

pytestmark = pytest.mark.skipif(
    not (RUNNER / "agents" / "agent.py").exists(),
    reason="runner not vendored; run scripts/vendor_framework.sh",
)

sys.path.insert(0, str(AGI3 / "scripts"))


def test_the_submitted_agent_plays_a_game_from_disk(tmp_path: Path, capsys) -> None:
    import play_offline

    out = tmp_path / "result.json"
    assert play_offline.main([str(FIXTURES), "--max-actions", "60", "--json-out", str(out)]) == 0

    result = json.loads(out.read_text())
    ours = result["results"]["myagent"]
    floor = result["results"]["random"]

    by_id = {game["game_id"]: game for game in ours["games"]}
    assert set(by_id) == {"tw01", "tc01"}
    for game_id, game in by_id.items():
        # tw01 is only solvable by walking, tc01 only by clicking the right
        # cell, so a win on both means the router sent each to the right policy
        # and the click carried its coordinates.
        assert game["state"] == "WIN", game_id
        assert game["levels_completed"] == game["win_levels"] == 2, game_id
    assert ours["score"] > 0  # the official scorecard was computed
    for game in floor["games"]:
        assert game["levels_completed"] <= by_id[game["game_id"]]["levels_completed"]


def test_an_unknown_game_is_refused_with_the_list(capsys) -> None:
    import play_offline

    assert play_offline.main([str(FIXTURES), "--games", "zz99"]) == 2
    assert "tw01" in capsys.readouterr().out


def test_an_empty_directory_is_refused(tmp_path: Path, capsys) -> None:
    import play_offline

    assert play_offline.main([str(tmp_path)]) == 2
