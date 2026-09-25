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
    assert play_offline.main([str(FIXTURES), "--max-actions", "400", "--json-out", str(out)]) == 0

    result = json.loads(out.read_text())
    ours = result["results"]["myagent"]
    floor = result["results"]["random"]

    by_id = {game["game_id"]: game for game in ours["games"]}
    assert set(by_id) == {"tw01", "tc01", "tc02"}
    for game_id, game in by_id.items():
        # tw01 is only solvable by walking, tc01 and tc02 only by clicking the
        # right cell, so a win on all three means the router sent each to the
        # right policy (or switched to it) and the click carried its coordinates.
        assert game["state"] == "WIN", game_id
        assert game["levels_completed"] == game["win_levels"] == 2, game_id
    # tc02 offers directions, so it is walked first and cleared only by switching.
    assert by_id["tc02"]["used"] == ["navigator", "clicker"]
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


def _results(walked: list[tuple[str, int, int]], clicked: int = 0) -> dict:
    ours = [{"game_id": g, "policy": "navigator", "levels_completed": o} for g, o, _ in walked]
    floor = [{"game_id": g, "policy": "random", "levels_completed": r} for g, _, r in walked]
    ours += [{"game_id": f"c{i}", "policy": "clicker", "levels_completed": 9} for i in range(clicked)]
    floor += [{"game_id": f"c{i}", "policy": "random", "levels_completed": 0} for i in range(clicked)]
    return {"myagent": {"games": ours}, "random": {"games": floor}}


def test_mock_comparison_uses_walked_games_only():
    """Clicked games are not what the mock modelled, so they must not sway it."""
    import play_offline

    result = play_offline.compare_with_mock(_results([("w1", 0, 1)], clicked=3))
    assert result["walked_games"] == 1
    assert result["outcome"].startswith("held")


def test_mock_comparison_outcomes():
    import play_offline

    compare = play_offline.compare_with_mock
    assert compare(_results([("w1", 2, 0)]))["outcome"].startswith("REVERSED")
    assert compare(_results([("w1", 1, 1)]))["outcome"].startswith("tied")
    assert compare(_results([]))["outcome"].startswith("no walked games")
