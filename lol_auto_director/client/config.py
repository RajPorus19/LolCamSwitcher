"""Client agent configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClientConfig:
    """Config for the event relay client (standalone or server-connected)."""

    player_id: str = "A"  # "A" or "B"
    summoner_name: str = ""
    server_url: str = ""  # e.g. http://vps.example.com:8750
    api_token: str = ""
    relay_enabled: bool = False
    poll_interval_ms: int = 500
    riot_live_client_url: str = "https://127.0.0.1:2999"

    @property
    def relay_configured(self) -> bool:
        return self.relay_enabled and bool(self.server_url.strip()) and bool(self.api_token.strip())
