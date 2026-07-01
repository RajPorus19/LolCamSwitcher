"""Shared API schemas for client ↔ server communication."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EventPayload(BaseModel):
    """Game event sent from client to server."""

    player: Literal["A", "B"]
    type: str = Field(..., description="EventType value, e.g. kill")
    time: float = Field(..., ge=0, description="Game time in seconds")
    summoner_name: str = ""


class HeartbeatPayload(BaseModel):
    """Periodic client heartbeat with current game time."""

    player: Literal["A", "B"]
    game_time: float = Field(..., ge=0)
    summoner_name: str = ""
    lol_connected: bool = True


class StatusResponse(BaseModel):
    """Director status returned by the server."""

    game_time: float
    focus: str
    focus_start: float = 0.0
    focus_end: float = 0.0
    last_reason: str = ""
    score_a: float
    score_b: float
    last_event: str | None
    clients_connected: list[str]
    obs_connected: bool
    auto_mode: bool
    debug_mode: bool = False


class IngestResponse(BaseModel):
    accepted: bool
    message: str = ""
