"""Event types and scoring values for LoL auto director."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    KILL = "kill"
    SOLO_KILL = "solo_kill"
    OUTPLAY = "outplay"
    DOUBLE_KILL = "double_kill"
    TRIPLE_KILL = "triple_kill"
    QUADRA_KILL = "quadra_kill"
    PENTA_KILL = "penta_kill"
    ASSIST = "assist"
    FIRST_BLOOD = "first_blood"
    ENGAGE = "engage"
    DEATH = "death"
    OBJECTIVE = "objective"
    CONTESTED_OBJECTIVE = "contested_objective"
    DRAGON = "dragon"
    BARON = "baron"
    HERALD = "herald"
    TURRET = "turret"
    FIRST_TURRET = "first_turret"
    INHIBITOR = "inhibitor"
    ACE = "ace"
    LOW_HP = "low_hp"
    HEAVY_TRADE = "heavy_trade"
    COMBAT_NEARBY = "combat_nearby"
    MOVING_TO_ACTION = "moving_to_action"
    FARM = "farm"


# Instant interest points — "how interesting is this action right now?"
EVENT_SCORES: dict[EventType, int] = {
    EventType.KILL: 100,
    EventType.SOLO_KILL: 120,
    EventType.OUTPLAY: 120,
    EventType.DOUBLE_KILL: 150,
    EventType.TRIPLE_KILL: 200,
    EventType.QUADRA_KILL: 250,
    EventType.PENTA_KILL: 300,
    EventType.ASSIST: 40,
    EventType.FIRST_BLOOD: 120,
    EventType.ENGAGE: 80,
    EventType.DEATH: 15,
    EventType.OBJECTIVE: 100,
    EventType.CONTESTED_OBJECTIVE: 100,
    EventType.DRAGON: 100,
    EventType.BARON: 120,
    EventType.HERALD: 90,
    EventType.TURRET: 70,
    EventType.FIRST_TURRET: 90,
    EventType.INHIBITOR: 100,
    EventType.ACE: 150,
    EventType.LOW_HP: 50,
    EventType.HEAVY_TRADE: 60,
    EventType.COMBAT_NEARBY: 60,
    EventType.MOVING_TO_ACTION: 30,
    EventType.FARM: 10,
}

EVENT_REASON_LABELS: dict[EventType, str] = {
    EventType.KILL: "KILL",
    EventType.SOLO_KILL: "SOLO KILL",
    EventType.OUTPLAY: "OUTPLAY",
    EventType.DOUBLE_KILL: "DOUBLE KILL",
    EventType.TRIPLE_KILL: "TRIPLE KILL",
    EventType.QUADRA_KILL: "QUADRA KILL",
    EventType.PENTA_KILL: "PENTAKILL",
    EventType.ASSIST: "ASSIST",
    EventType.FIRST_BLOOD: "FIRST BLOOD",
    EventType.ENGAGE: "ENGAGE",
    EventType.DEATH: "DEATH",
    EventType.OBJECTIVE: "OBJECTIVE",
    EventType.CONTESTED_OBJECTIVE: "CONTESTED OBJECTIVE",
    EventType.DRAGON: "DRAGON FIGHT",
    EventType.BARON: "BARON FIGHT",
    EventType.HERALD: "HERALD",
    EventType.TURRET: "TURRET",
    EventType.FIRST_TURRET: "FIRST TURRET",
    EventType.INHIBITOR: "INHIBITOR",
    EventType.ACE: "TEAMFIGHT",
    EventType.LOW_HP: "LOW HP COMBAT",
    EventType.HEAVY_TRADE: "HEAVY TRADE",
    EventType.COMBAT_NEARBY: "HEAVY TRADE",
    EventType.MOVING_TO_ACTION: "MOVING TO ACTION",
    EventType.FARM: "FARM",
}

# Priority tier (lower = higher priority in clash resolution)
EVENT_PRIORITY: dict[EventType, int] = {
    EventType.PENTA_KILL: 1,
    EventType.QUADRA_KILL: 1,
    EventType.TRIPLE_KILL: 1,
    EventType.KILL: 1,
    EventType.SOLO_KILL: 1,
    EventType.OUTPLAY: 1,
    EventType.DOUBLE_KILL: 1,
    EventType.ASSIST: 1,
    EventType.FIRST_BLOOD: 1,
    EventType.ACE: 1,
    EventType.BARON: 2,
    EventType.DRAGON: 2,
    EventType.CONTESTED_OBJECTIVE: 2,
    EventType.HERALD: 2,
    EventType.INHIBITOR: 2,
    EventType.OBJECTIVE: 2,
    EventType.FIRST_TURRET: 2,
    EventType.TURRET: 2,
    EventType.HEAVY_TRADE: 3,
    EventType.COMBAT_NEARBY: 3,
    EventType.LOW_HP: 3,
    EventType.DEATH: 3,
    EventType.MOVING_TO_ACTION: 4,
    EventType.ENGAGE: 4,
    EventType.FARM: 5,
}

MAJOR_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.KILL,
        EventType.SOLO_KILL,
        EventType.OUTPLAY,
        EventType.DOUBLE_KILL,
        EventType.TRIPLE_KILL,
        EventType.QUADRA_KILL,
        EventType.PENTA_KILL,
        EventType.FIRST_BLOOD,
        EventType.OBJECTIVE,
        EventType.CONTESTED_OBJECTIVE,
        EventType.DRAGON,
        EventType.BARON,
        EventType.INHIBITOR,
        EventType.ACE,
    }
)

# Bypass minimum focus lock — pentakill, major teamfight, baron/dragon
CRITICAL_EVENT_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.PENTA_KILL,
        EventType.QUADRA_KILL,
        EventType.ACE,
        EventType.BARON,
        EventType.DRAGON,
        EventType.CONTESTED_OBJECTIVE,
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

    @property
    def is_critical(self) -> bool:
        return self.type in CRITICAL_EVENT_TYPES

    @property
    def reason_label(self) -> str:
        return EVENT_REASON_LABELS.get(
            self.type, self.type.value.upper().replace("_", " ")
        )

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
