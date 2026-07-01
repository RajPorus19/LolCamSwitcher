"""Event source protocol — local Riot API or remote client ingest."""

from __future__ import annotations

from typing import Protocol

from lol_cam_switcher.lol.events import GameEvent


class EventSource(Protocol):
    def is_available(self) -> bool: ...
    def get_game_time(self) -> float: ...
    def poll_events(self) -> list[GameEvent]: ...
    def close(self) -> None: ...
