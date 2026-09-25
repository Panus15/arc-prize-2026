"""Tests for the live-recording summariser.

The point of this file is that the parser is checked against the real schema
rather than against what we assumed it was. Frames are built with the actual
`FrameData` model and written out through `model_dump_json`, which is exactly
what the official runner's recorder does, so a field that does not exist on the
model cannot quietly pass here.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from arcengine import FrameData

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from summarise_live import GameSummary, main, read_recording  # noqa: E402


def write_recording(
    directory: Path,
    game_id: str,
    *,
    steps: list[tuple[int, int]],
    final_state: str,
    win_levels: int = 3,
) -> Path:
    """Write a recording the way agents/recorder.py does: one JSON event per line."""
    path = directory / f"{game_id}.navigator.100.abc.recording.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for index, (action_id, levels) in enumerate(steps):
            frame = FrameData(
                game_id=game_id,
                frame=[[[0, 0], [0, 0]]],
                state=final_state if index == len(steps) - 1 else "NOT_FINISHED",
                levels_completed=levels,
                win_levels=win_levels,
                action_input={"id": action_id, "data": {}},
                available_actions=[1, 2, 3, 4],
                guid="guid",
                full_reset=False,
            )
            event = {
                "timestamp": datetime.now(UTC).isoformat(),
                "data": json.loads(frame.model_dump_json()),
            }
            handle.write(json.dumps(event) + "\n")
    return path


def test_real_framedata_carries_levels_not_score() -> None:
    """Guards the assumption the parser rests on."""
    fields = set(FrameData.model_fields)
    assert {"levels_completed", "win_levels"} <= fields
    assert "score" not in fields


def test_reads_a_lost_game(tmp_path: Path) -> None:
    write_recording(tmp_path, "ls20", steps=[(1, 0), (2, 0), (3, 0)], final_state="GAME_OVER")
    summary = read_recording(next(tmp_path.glob("*.recording.jsonl")))
    assert summary is not None
    assert summary.game_id == "ls20"
    assert summary.actions == 3
    assert summary.levels_completed == 0
    assert summary.win_levels == 3
    assert not summary.won
    assert summary.action_counts == {1: 1, 2: 1, 3: 1}


def test_reads_a_won_game(tmp_path: Path) -> None:
    write_recording(tmp_path, "ft09", steps=[(6, 1), (6, 2), (6, 3)], final_state="WIN")
    summary = read_recording(next(tmp_path.glob("*.recording.jsonl")))
    assert summary is not None
    assert summary.won
    assert summary.levels_completed == 3
    assert summary.line() == "ft09       WIN  3/3 levels in 3 actions"


def test_scorecard_lines_are_not_counted_as_frames(tmp_path: Path) -> None:
    """The recorder also writes scorecards; they have no `state` and must be skipped."""
    path = write_recording(tmp_path, "vc33", steps=[(1, 0)], final_state="GAME_OVER")
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": "t", "data": {"played_actions": 999}}) + "\n")
    summary = read_recording(path)
    assert summary is not None
    assert summary.actions == 1


def test_empty_directory_is_reported_not_crashed(tmp_path: Path, capsys) -> None:
    assert main([str(tmp_path)]) == 2
    assert "no *.recording.jsonl" in capsys.readouterr().out


def test_no_verdict_is_drawn_without_a_floor(tmp_path: Path, capsys) -> None:
    """A recording alone cannot test the mock: that needs random on the same games."""
    write_recording(tmp_path, "ls20", steps=[(1, 1)], final_state="GAME_OVER")
    assert main([str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "prediction" not in out.lower()
    assert "play_offline.py" in out


def test_json_out_round_trips(tmp_path: Path) -> None:
    write_recording(tmp_path, "ls20", steps=[(1, 0), (5, 1)], final_state="GAME_OVER")
    out = tmp_path / "live.json"
    assert main([str(tmp_path), "--json-out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["totals"] == {
        "games": 1,
        "games_won": 0,
        "levels_cleared": 1,
        "actions": 2,
    }
    assert payload["games"][0]["action_counts"] == {"1": 1, "5": 1}


def test_summary_line_handles_an_unknown_target() -> None:
    assert "0/? levels" in GameSummary(game_id="x", final_state="GAME_OVER").line()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
