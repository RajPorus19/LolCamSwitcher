"""Riot Live Client Data API — Vanguard-safe, no memory access."""

from __future__ import annotations

import logging
import ssl
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from lol_auto_director.lol.events import EventType, GameEvent

logger = logging.getLogger(__name__)

# Riot Live Client uses a self-signed certificate
_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE


class _InsecureAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = _SSL_CONTEXT
        return super().init_poolmanager(*args, **kwargs)


class RiotLiveClientAPI:
    """
    Polls the local Live Client Data API (port 2999).

    Available only while a game is running on the same machine.
    No injection, no memory reading — fully Vanguard compatible.
    """

    def __init__(
        self,
        base_url: str = "https://127.0.0.1:2999",
        player_a_name: str = "",
        player_b_name: str = "",
    ):
        self.base_url = base_url.rstrip("/")
        self.player_a_name = player_a_name.lower()
        self.player_b_name = player_b_name.lower()
        self._session = requests.Session()
        self._session.mount("https://", _InsecureAdapter())
        self._session.verify = False
        self._seen_event_ids: set[str] = set()
        self._last_game_time: float = 0.0
        self._prev_hp: dict[str, float] = {}
        self._low_hp_cooldown: dict[str, float] = {}

    def is_available(self) -> bool:
        try:
            resp = self._session.get(f"{self.base_url}/liveclientdata/gamestats", timeout=1.0)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    def get_game_time(self) -> float:
        stats = self._get_json("/liveclientdata/gamestats")
        if stats is None:
            return self._last_game_time
        self._last_game_time = float(stats.get("gameTime", 0.0))
        return self._last_game_time

    def get_active_player(self) -> dict[str, Any] | None:
        return self._get_json("/liveclientdata/activeplayer")

    def get_all_players(self) -> list[dict[str, Any]]:
        data = self._get_json("/liveclientdata/playerlist")
        return data if isinstance(data, list) else []

    def poll_events(self) -> list[GameEvent]:
        """Fetch new events since last poll."""
        new_events: list[GameEvent] = []

        raw_events = self._get_json("/liveclientdata/eventdata")
        if raw_events and "Events" in raw_events:
            for raw in raw_events["Events"]:
                event_id = raw.get("EventID", str(raw))
                if event_id in self._seen_event_ids:
                    continue
                self._seen_event_ids.add(event_id)
                mapped = self._map_riot_event(raw)
                if mapped:
                    new_events.append(mapped)

        new_events.extend(self._poll_player_stats())
        return new_events

    def _poll_player_stats(self) -> list[GameEvent]:
        """Detect low HP and combat from player stat polling (Vanguard-safe)."""
        players = self.get_all_players()
        if not players:
            return []

        events: list[GameEvent] = []
        game_time = self._last_game_time

        for p in players:
            name = p.get("summonerName", p.get("riotId", ""))
            player_id = self._resolve_player(name)
            if player_id is None:
                continue

            current_hp = float(p.get("currentHealth", 0))
            max_hp = float(p.get("maxHealth", 1))
            hp_ratio = current_hp / max_hp if max_hp > 0 else 1.0

            prev = self._prev_hp.get(player_id, current_hp)
            damage_taken = prev - current_hp
            self._prev_hp[player_id] = current_hp

            if damage_taken > max_hp * 0.08 and game_time > 0:
                events.append(
                    GameEvent(EventType.COMBAT_NEARBY, player_id, game_time, raw=p)
                )

            last_low = self._low_hp_cooldown.get(player_id, 0.0)
            if hp_ratio < 0.25 and game_time - last_low > 15.0:
                self._low_hp_cooldown[player_id] = game_time
                events.append(
                    GameEvent(EventType.LOW_HP, player_id, game_time, raw=p)
                )

        return events

    def _get_json(self, path: str) -> Any | None:
        try:
            resp = self._session.get(f"{self.base_url}{path}", timeout=1.5)
            if resp.status_code == 200:
                return resp.json()
        except requests.RequestException as exc:
            logger.debug("Riot API request failed: %s", exc)
        return None

    def _resolve_player(self, summoner_name: str) -> str | None:
        name = summoner_name.lower()
        if name == self.player_a_name:
            return "A"
        if name == self.player_b_name:
            return "B"
        return None

    def _map_riot_event(self, raw: dict[str, Any]) -> GameEvent | None:
        event_name = raw.get("EventName", "")
        event_time = float(raw.get("EventTime", self._last_game_time))

        if event_name == "ChampionKill":
            killer = raw.get("KillerName", "")
            player = self._resolve_player(killer)
            if player is None:
                return None
            return GameEvent(EventType.KILL, player, event_time, raw=raw)

        if event_name == "Multikill":
            killer = raw.get("KillerName", "")
            player = self._resolve_player(killer)
            kill_streak = int(raw.get("KillStreak", 2))
            if player is None:
                return None
            event_type = EventType.DOUBLE_KILL if kill_streak >= 2 else EventType.KILL
            return GameEvent(event_type, player, event_time, raw=raw)

        if event_name == "DragonKill":
            killer = raw.get("KillerName", "")
            player = self._resolve_player(killer) or "A"
            return GameEvent(EventType.OBJECTIVE, player, event_time, raw=raw)

        if event_name == "BaronKill":
            killer = raw.get("KillerName", "")
            player = self._resolve_player(killer) or "A"
            return GameEvent(EventType.OBJECTIVE, player, event_time, raw=raw)

        if event_name == "TurretKilled":
            killer = raw.get("KillerName", "")
            player = self._resolve_player(killer) or "A"
            return GameEvent(EventType.OBJECTIVE, player, event_time, raw=raw)

        if event_name == "ChampionDeath":
            victim = raw.get("VictimName", "")
            player = self._resolve_player(victim)
            if player is None:
                return None
            return GameEvent(EventType.DEATH, player, event_time, raw=raw)

        return None

    def reset(self) -> None:
        self._seen_event_ids.clear()
        self._last_game_time = 0.0
        self._prev_hp.clear()
        self._low_hp_cooldown.clear()

    def close(self) -> None:
        self._session.close()
