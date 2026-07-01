"""Tests for per-game session logging."""

import tempfile
from pathlib import Path

from lol_cam_switcher.director.priority import FocusTarget
from lol_cam_switcher.director.timeline import FocusDecision
from lol_cam_switcher.lol.events import EventType, GameEvent
from lol_cam_switcher.session_log.game_logger import GameSessionLogger, format_game_time


def test_format_game_time():
    assert format_game_time(1530) == "25:30"


def test_session_creates_log_file():
    lines: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        log = GameSessionLogger(logs_dir=Path(tmp), on_line=lines.append)
        log.tick(api_available=True, game_time=10.0)
        log.log_info("hello", 10.0)
        assert log.in_session
        assert log.current_log_path is not None
        assert log.current_log_path.name.startswith("game_")
        log.end_session()
        content = log.current_log_path.read_text(encoding="utf-8") if log.current_log_path else ""
        # path cleared after end — read from list
        files = list(Path(tmp).glob("game_*.log"))
        assert len(files) == 1
        assert "hello" in files[0].read_text(encoding="utf-8")
        assert len(lines) >= 2


def test_event_and_camera_log_lines():
    with tempfile.TemporaryDirectory() as tmp:
        log = GameSessionLogger(logs_dir=Path(tmp))
        log.tick(True, 100.0)
        event = GameEvent(EventType.KILL, "A", 120.0)
        decision = FocusDecision.from_event(event, pre_delay=3.0, post_focus=12.0)
        log.log_event(event, decision, 120.0)
        log.log_camera_switch("PLAYER_A", FocusTarget.PLAYER_A, 117.0, obs_connected=True)
        text = log.list_log_files()[0].read_text(encoding="utf-8")
        assert "EVENT" in text
        assert "kill" in text
        assert "CAMERA" in text
        assert "01:57" in text or "01:57" in text  # focus start 117s
