"""Event types and scoring values for LoL auto director."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    KILL = "kill"
    DOUBLE_KILL = "double_kill"
    TRIPLE_KILL = "triple_kill"
    QUADRA_KILL = "quadra_kill"
    PENTA_KILL = "penta_kill"
    ASSIST = "assist"
    FIRST_BLOOD = "first_blood"
    ENGAGE = "engage"
    DEATH = "death"
    OBJECTIVE = "objective"
    DRAGON = "dragon"
    BARON = "baron"
    HERALD = "herald"
    TURRET = "turret"
    FIRST_TURRET = "first_turret"
    INHIBITOR = "inhibitor"
    ACE = "ace"
    LOW_HP = "low_hp"
    COMBAT_NEARBY = "combat_nearby"
    FARM = "farm"


# Points awarded per event type
EVENT_SCORES: dict[EventType, int] = {
    EventType.KILL: 100,
    EventType.DOUBLE_KILL: 200,
    EventType.TRIPLE_KILL: 300,
    EventType.QUADRA_KILL: 400,
    EventType.PENTA_KILL: 500,
    EventType.ASSIST: 50,
    EventType.FIRST_BLOOD: 150,
    EventType.ENGAGE: 60,
    EventType.DEATH: 20,
    EventType.OBJECTIVE: 120,
    EventType.DRAGON: 120,
    EventType.BARON: 150,
    EventType.HERALD: 110,
    EventType.TURRET: 80,
    EventType.FIRST_TURRET: 100,
    EventType.INHIBITOR: 130,
    EventType.ACE: 180,
    EventType.LOW_HP: 40,
    EventType.COMBAT_NEARBY: 30,
    EventType.FARM: 10,
}

# Priority tier (lower = higher priority in clash resolution)
EVENT_PRIORITY: dict[EventType, int] = {
    EventType.PENTA_KILL: 1,
    EventType.QUADRA_KILL: 1,
    EventType.TRIPLE_KILL: 1,
    EventType.KILL: 1,
    EventType.DOUBLE_KILL: 1,
    EventType.ASSIST: 1,
    EventType.FIRST_BLOOD: 1,
    EventType.ACE: 1,
    EventType.BARON: 2,
    EventType.DRAGON: 2,
    EventType.HERALD: 2,
    EventType.INHIBITOR: 2,
    EventType.OBJECTIVE: 2,
    EventType.FIRST_TURRET: 2,
    EventType.TURRET: 2,
    EventType.COMBAT_NEARBY: 3,
    EventType.LOW_HP: 3,
    EventType.DEATH: 3,
    EventType.ENGAGE: 4,
    EventType.FARM: 5,
}

MAJOR_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.KILL,
        EventType.DOUBLE_KILL,
        EventType.TRIPLE_KILL,
        EventType.QUADRA_KILL,
        EventType.PENTA_KILL,
        EventType.FIRST_BLOOD,
        EventType.OBJECTIVE,
        EventType.DRAGON,
        EventType.BARON,
        EventType.INHIBITOR,
        EventType.ACE,
    }
)

MULTIKILL_EVENT_BY_STREAK: dict[int, EventType] = {
    2: EventType.DOUBLE_KILL,
    3: EventType.TRIPLE_KILL,
    4: EventType.QUADRA_KILL,
    5: EventType.PENTA_KILL,
}


def multikill_type(kill_streak: int) -> EventType:
    if kill_streak >= 5:
        return EventType.PENTA_KILL
    return MULTIKILL_EVENT_BY_STREAK.get(kill_streak, EventType.KILL)


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
