"""Per-game session logging — one file per match, readable timeline."""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, TextIO

from lol_cam_switcher.director.priority import FocusTarget
from lol_cam_switcher.director.timeline import DirectorState, FocusDecision
from lol_cam_switcher.lol.events import GameEvent


def default_logs_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LolCamSwitcher" / "logs"
    else:
        base = Path.home() / ".lol-cam-switcher" / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def format_game_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


FOCUS_LABELS = {
    FocusTarget.PLAYER_A: "PLAYER_A",
    FocusTarget.PLAYER_B: "PLAYER_B",
    FocusTarget.SPLIT_SCREEN: "SPLIT",
}


class GameSessionLogger:
    """
    Writes one log file per LoL game session.

    Filename pattern: game_YYYY-MM-DD_HHMMSS.log
    """

    def __init__(
        self,
        logs_dir: Path | None = None,
        on_line: Callable[[str], None] | None = None,
    ):
        self.logs_dir = logs_dir or default_logs_dir()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.on_line = on_line
        self._lock = threading.Lock()
        self._file: TextIO | None = None
        self._session_path: Path | None = None
        self._session_start: datetime | None = None
        self._in_session = False
        self._last_game_time: float = -1.0
        self._unavailable_ticks = 0
        self._lines: list[str] = []
        self._max_memory_lines = 2000

    @property
    def current_log_path(self) -> Path | None:
        return self._session_path

    @property
    def in_session(self) -> bool:
        return self._in_session

    @property
    def live_lines(self) -> list[str]:
        with self._lock:
            return list(self._lines)

    def list_log_files(self) -> list[Path]:
        return sorted(self.logs_dir.glob("game_*.log"), reverse=True)

    def read_log_file(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def tick(self, api_available: bool, game_time: float) -> None:
        """Detect game session start/end from API availability and game time."""
        with self._lock:
            if api_available:
                self._unavailable_ticks = 0
                if self._is_new_game(game_time):
                    self._end_session_unlocked(reason="new game detected")
                    self._start_session_unlocked(game_time)
                elif not self._in_session:
                    self._start_session_unlocked(game_time)
                self._last_game_time = game_time
            else:
                self._unavailable_ticks += 1
                if self._in_session and self._unavailable_ticks >= 6:
                    self._end_session_unlocked(reason="LoL API unavailable (game ended?)")

    def log_event(
        self,
        event: GameEvent,
        decision: FocusDecision | None,
        game_time: float,
    ) -> None:
        pre = f"focus {format_game_time(decision.start_time)}→{format_game_time(decision.end_time)}"
        if decision:
            target = FOCUS_LABELS.get(decision.target, decision.target.value)
            detail = (
                f"Player {event.player} — {event.type.value} (+{event.score}) | "
                f"target {target} | {pre} | pre-delay -{decision.pre_event_delay:.0f}s"
            )
        else:
            detail = f"Player {event.player} — {event.type.value} (+{event.score})"
        self._write("EVENT", detail, game_time)

    def log_focus_decision(
        self,
        focus: FocusTarget,
        game_time: float,
        *,
        reason: str = "",
        score_a: float = 0.0,
        score_b: float = 0.0,
        focus_start: float = 0.0,
        focus_end: float = 0.0,
        last_event: GameEvent | None = None,
    ) -> None:
        label = FOCUS_LABELS.get(focus, focus.value)
        detail = f"FOCUS {label}"
        if reason:
            detail += f" | Reason: {reason}"
        if focus_start > 0:
            detail += (
                f" | Window {format_game_time(focus_start)}→{format_game_time(focus_end)}"
            )
        detail += f" | Score A={score_a:.0f} B={score_b:.0f}"
        if last_event:
            detail += f" | Event: {last_event.type.value} ({last_event.player})"
        self._write("FOCUS", detail, game_time)

    def log_director_decision(
        self,
        event: GameEvent,
        state: DirectorState,
        decision: FocusDecision | None,
        game_time: float,
    ) -> None:
        """Structured esport-style decision block for debug mode."""
        focus_label = FOCUS_LABELS.get(state.focus, state.focus.value)
        lines = [
            f"[{format_game_time(game_time)}]",
            f"{event.type.value.upper()} détecté PLAYER_{event.player}",
            "Score:",
            f"PLAYER_A {state.score_a:.0f}",
            f"PLAYER_B {state.score_b:.0f}",
            "Decision:",
            f"FOCUS {focus_label}",
            "Reason:",
            decision.reason if decision else event.reason_label,
        ]
        self._write("DECISION", "\n".join(lines), game_time)

    def log_camera_switch(
        self,
        scene_name: str,
        focus: FocusTarget,
        game_time: float,
        *,
        obs_connected: bool,
        trigger: str = "auto",
    ) -> None:
        label = FOCUS_LABELS.get(focus, focus.value)
        if obs_connected:
            detail = (
                f"Camera switched to {label} (scene: {scene_name}) at game time "
                f"{format_game_time(game_time)} [{trigger}]"
            )
            kind = "CAMERA"
        else:
            detail = (
                f"Camera switch requested → {label} (scene: {scene_name}) at game time "
                f"{format_game_time(game_time)} [OBS not connected, skipped]"
            )
            kind = "CAMERA_SKIP"
        self._write(kind, detail, game_time)

    def log_info(self, message: str, game_time: float | None = None) -> None:
        gt = game_time if game_time is not None else self._last_game_time
        self._write("INFO", message, max(0.0, gt))

    def end_session(self, reason: str = "manual stop") -> None:
        with self._lock:
            self._end_session_unlocked(reason=reason)

    def _is_new_game(self, game_time: float) -> bool:
        if not self._in_session:
            return False
        if self._last_game_time > 120 and game_time < 30:
            return True
        return False

    def _start_session_unlocked(self, game_time: float) -> None:
        self._session_start = datetime.now()
        stamp = self._session_start.strftime("%Y-%m-%d_%H%M%S")
        self._session_path = self.logs_dir / f"game_{stamp}.log"
        self._file = self._session_path.open("a", encoding="utf-8")
        self._in_session = True
        header = (
            f"=== LolCamSwitcher — game session {self._session_start.isoformat(timespec='seconds')} ==="
        )
        self._append_line(header, game_time=0.0, kind="SESSION")
        self._append_line(f"Log file: {self._session_path}", game_time=0.0, kind="SESSION")

    def _end_session_unlocked(self, reason: str) -> None:
        if not self._in_session:
            return
        self._append_line(f"Session ended — {reason}", game_time=self._last_game_time, kind="SESSION")
        if self._file:
            self._file.close()
            self._file = None
        self._in_session = False
        self._session_path = None
        self._session_start = None

    def _write(self, kind: str, detail: str, game_time: float) -> None:
        with self._lock:
            if not self._in_session and kind != "SESSION":
                self._start_session_unlocked(game_time)
            self._append_line(detail, game_time=game_time, kind=kind)

    def _append_line(self, detail: str, game_time: float, kind: str) -> None:
        wall = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        gt = format_game_time(game_time)
        line = f"[{wall}] [GAME {gt}] {kind:<12} {detail}"
        self._lines.append(line)
        if len(self._lines) > self._max_memory_lines:
            self._lines = self._lines[-self._max_memory_lines :]
        if self._file:
            self._file.write(line + "\n")
            self._file.flush()
        if self.on_line:
            self.on_line(line)
