"""Event types and scoring values for LoL auto director."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    KILL = "kill"
    DOUBLE_KILL = "double_kill"
    ASSIST = "assist"
    ENGAGE = "engage"
    DEATH = "death"
    OBJECTIVE = "objective"
    LOW_HP = "low_hp"
    COMBAT_NEARBY = "combat_nearby"
    FARM = "farm"


# Points awarded per event type
EVENT_SCORES: dict[EventType, int] = {
    EventType.KILL: 100,
    EventType.DOUBLE_KILL: 200,
    EventType.ASSIST: 50,
    EventType.ENGAGE: 60,
    EventType.DEATH: 20,
    EventType.OBJECTIVE: 120,
    EventType.LOW_HP: 40,
    EventType.COMBAT_NEARBY: 30,
    EventType.FARM: 10,
}

# Priority tier (lower = higher priority in clash resolution)
EVENT_PRIORITY: dict[EventType, int] = {
    EventType.KILL: 1,
    EventType.DOUBLE_KILL: 1,
    EventType.ASSIST: 1,
    EventType.OBJECTIVE: 2,
    EventType.COMBAT_NEARBY: 3,
    EventType.ENGAGE: 4,
    EventType.LOW_HP: 3,
    EventType.DEATH: 3,
    EventType.FARM: 5,
}

MAJOR_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.KILL,
        EventType.DOUBLE_KILL,
        EventType.OBJECTIVE,
    }
)


@dataclass
class GameEvent:
    """Single game event with timestamp in game seconds."""

    type: EventType
    player: str  # "A" or "B"
    time: float  # game time in seconds (e.g. 930 = 15:30)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        return EVENT_SCORES.get(self.type, 0)

    @property
    def priority_tier(self) -> int:
        return EVENT_PRIORITY.get(self.type, 99)

    @property
    def is_major(self) -> bool:
        return self.type in MAJOR_EVENT_TYPES

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "player": self.player,
            "time": self.time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameEvent:
        return cls(
            type=EventType(data["type"]),
            player=data["player"],
            time=float(data["time"]),
            raw=data.get("raw", {}),
        )

    def format_time(self) -> str:
        minutes = int(self.time // 60)
        seconds = int(self.time % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def __str__(self) -> str:
        return f"[{self.format_time()}] {self.player} — {self.type.value} (+{self.score})"
