"""Client engine — local LoL events, optional relay to regie server."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from lol_cam_switcher.client.config import ClientConfig
from lol_cam_switcher.client.relay import EventRelay
from lol_cam_switcher.lol.api import RiotLiveClientAPI
from lol_cam_switcher.lol.events import GameEvent

logger = logging.getLogger(__name__)


@dataclass
class ClientEngine:
    """
    Runs on each gaming PC.

    Standalone: polls Riot Live Client API locally, displays events.
    Relay mode: also forwards events + heartbeats to the regie server.
    """

    config: ClientConfig = field(default_factory=ClientConfig)
    on_state_changed: Callable[[], None] | None = None
    on_event: Callable[[GameEvent], None] | None = None

    riot_api: RiotLiveClientAPI = field(init=False)
    relay: EventRelay = field(init=False)

    _thread: threading.Thread | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_event: GameEvent | None = field(default=None, repr=False)
    _recent_events: list[GameEvent] = field(default_factory=list)
    _game_time: float = 0.0
    _server_connected: bool = False
    _heartbeat_counter: int = 0

    def __post_init__(self) -> None:
        self._build_riot_api()
        self.relay = EventRelay(self.config)

    def _build_riot_api(self) -> None:
        name = self.config.summoner_name
        self.riot_api = RiotLiveClientAPI(
            base_url=self.config.riot_live_client_url,
            player_a_name=name if self.config.player_id == "A" else "",
            player_b_name=name if self.config.player_id == "B" else "",
        )

    def apply_config(self, config: ClientConfig) -> None:
        with self._lock:
            self.config = config
            self._build_riot_api()
            self.relay.update_config(config)
        self._notify()

    @property
    def lol_connected(self) -> bool:
        return self.riot_api.is_available()

    @property
    def server_connected(self) -> bool:
        return self._server_connected

    @property
    def game_time(self) -> float:
        return self._game_time

    @property
    def last_event(self) -> GameEvent | None:
        return self._last_event

    @property
    def recent_events(self) -> list[GameEvent]:
        with self._lock:
            return list(self._recent_events)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ClientEngine")
        self._thread.start()
        logger.info("Client engine started (relay=%s)", self.config.relay_configured)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        self.riot_api.close()
        self.relay.close()
        logger.info("Client engine stopped")

    def test_server_connection(self) -> bool:
        self._server_connected = self.relay.check_connection()
        self._notify()
        return self._server_connected

    def _loop(self) -> None:
        interval = self.config.poll_interval_ms / 1000.0
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.exception("Client tick error")
            time.sleep(interval)

    def _tick(self) -> None:
        available = self.riot_api.is_available()
        game_time = self.riot_api.get_game_time() if available else self._game_time
        self._game_time = game_time

        new_events: list[GameEvent] = []
        if available:
            raw_events = self.riot_api.poll_events()
            for event in raw_events:
                # Force player slot to configured id for this client
                mapped = GameEvent(
                    event.type,
                    self.config.player_id,
                    event.time,
                    raw=event.raw,
                )
                new_events.append(mapped)

        with self._lock:
            for event in new_events:
                self._last_event = event
                self._recent_events.append(event)
                if len(self._recent_events) > 100:
                    self._recent_events = self._recent_events[-100:]
                if self.on_event:
                    self.on_event(event)

        if self.config.relay_configured:
            self._heartbeat_counter += 1
            if self._heartbeat_counter % 4 == 0:
                self._server_connected = self.relay.send_heartbeat(game_time, available)
            for event in new_events:
                if self.relay.send_event(event):
                    self._server_connected = True

        self._notify()

    def _notify(self) -> None:
        if self.on_state_changed:
            self.on_state_changed()
