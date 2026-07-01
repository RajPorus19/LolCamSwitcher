"""HTTP relay — send events and heartbeats to the regie server."""

from __future__ import annotations

import logging

import requests

from lol_auto_director.client.config import ClientConfig
from lol_auto_director.lol.events import GameEvent

logger = logging.getLogger(__name__)


class EventRelay:
    """POST events to the central regie server with Bearer token auth."""

    def __init__(self, config: ClientConfig):
        self.config = config
        self._session = requests.Session()
        self._session.headers.update(self._auth_headers())
        self._last_error: str = ""

    @property
    def last_error(self) -> str:
        return self._last_error

    def _auth_headers(self) -> dict[str, str]:
        token = self.config.api_token.strip()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def update_config(self, config: ClientConfig) -> None:
        self.config = config
        self._session.headers.update(self._auth_headers())

    def _url(self, path: str) -> str:
        return f"{self.config.server_url.rstrip('/')}{path}"

    def check_connection(self) -> bool:
        if not self.config.relay_configured:
            return False
        try:
            resp = self._session.get(self._url("/health"), timeout=3.0)
            if resp.status_code != 200:
                self._last_error = f"health HTTP {resp.status_code}"
                return False
            resp = self._session.get(self._url("/api/v1/status"), timeout=3.0)
            ok = resp.status_code == 200
            if not ok:
                self._last_error = f"auth/status HTTP {resp.status_code}"
            return ok
        except requests.RequestException as exc:
            self._last_error = str(exc)
            return False

    def send_event(self, event: GameEvent) -> bool:
        if not self.config.relay_configured:
            return False
        payload = {
            "player": event.player,
            "type": event.type.value,
            "time": event.time,
            "summoner_name": self.config.summoner_name,
        }
        try:
            resp = self._session.post(
                self._url("/api/v1/events"),
                json=payload,
                timeout=3.0,
            )
            if resp.status_code >= 400:
                self._last_error = f"events HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning("Relay event failed: %s", self._last_error)
                return False
            return True
        except requests.RequestException as exc:
            self._last_error = str(exc)
            logger.warning("Relay event error: %s", exc)
            return False

    def send_heartbeat(self, game_time: float, lol_connected: bool) -> bool:
        if not self.config.relay_configured:
            return False
        payload = {
            "player": self.config.player_id,
            "game_time": game_time,
            "summoner_name": self.config.summoner_name,
            "lol_connected": lol_connected,
        }
        try:
            resp = self._session.post(
                self._url("/api/v1/heartbeat"),
                json=payload,
                timeout=3.0,
            )
            if resp.status_code >= 400:
                self._last_error = f"heartbeat HTTP {resp.status_code}"
                return False
            return True
        except requests.RequestException as exc:
            self._last_error = str(exc)
            return False

    def close(self) -> None:
        self._session.close()
