"""Server-side event hub — aggregates events from remote clients."""

from __future__ import annotations

import threading
import time
from collections import deque

from lol_auto_director.lol.events import EventType, GameEvent


class RemoteEventHub:
    """
    Implements EventSource for the regie server.

    Clients POST events and heartbeats; the director polls this hub.
    """

    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: deque[GameEvent] = deque()
        self._game_time: float = 0.0
        self._last_heartbeat: dict[str, float] = {}
        self._summoner_names: dict[str, str] = {}

    def ingest_event(
        self,
        player: str,
        event_type: str,
        event_time: float,
        summoner_name: str = "",
    ) -> GameEvent:
        try:
            etype = EventType(event_type)
        except ValueError as exc:
            raise ValueError(f"Unknown event type: {event_type}") from exc

        event = GameEvent(etype, player, event_time)
        with self._lock:
            self._pending.append(event)
            self._game_time = max(self._game_time, event_time)
            if summoner_name:
                self._summoner_names[player] = summoner_name
        return event

    def ingest_heartbeat(
        self,
        player: str,
        game_time: float,
        summoner_name: str = "",
        lol_connected: bool = True,
    ) -> None:
        with self._lock:
            if lol_connected:
                self._last_heartbeat[player] = time.monotonic()
                self._game_time = max(self._game_time, game_time)
                if summoner_name:
                    self._summoner_names[player] = summoner_name
            else:
                self._last_heartbeat.pop(player, None)

    def connected_clients(self) -> list[str]:
        now = time.monotonic()
        with self._lock:
            return [
                p
                for p, ts in self._last_heartbeat.items()
                if now - ts <= self.HEARTBEAT_TIMEOUT
            ]

    def is_available(self) -> bool:
        return len(self.connected_clients()) > 0

    def get_game_time(self) -> float:
        with self._lock:
            return self._game_time

    def poll_events(self) -> list[GameEvent]:
        with self._lock:
            events = list(self._pending)
            self._pending.clear()
            return events

    def close(self) -> None:
        with self._lock:
            self._pending.clear()
            self._last_heartbeat.clear()

    def reset(self) -> None:
        self.close()
        with self._lock:
            self._game_time = 0.0
            self._summoner_names.clear()
