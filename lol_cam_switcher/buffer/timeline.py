"""Event buffer — temporal storage for instant replay decisions."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from lol_cam_switcher.lol.events import GameEvent


@dataclass
class BufferedEvent:
    """Event stored in the temporal buffer with arrival metadata."""

    event: GameEvent
    arrival_time: float  # wall-clock or game time when received
    target_time: float  # event.time - PRE_EVENT_DELAY

    @classmethod
    def from_event(cls, event: GameEvent, pre_delay: float, arrival_time: float) -> BufferedEvent:
        return cls(
            event=event,
            arrival_time=arrival_time,
            target_time=event.time - pre_delay,
        )


@dataclass
class EventBuffer:
    """
    Ring buffer of game events for instant replay logic.

    When an event arrives at instant T, the director seeks to target_time = T - 3s.
    """

    max_size: int = 500
    pre_event_delay: float = 3.0
    _events: deque[BufferedEvent] = field(default_factory=deque)

    def push(self, event: GameEvent, current_game_time: float) -> BufferedEvent:
        buffered = BufferedEvent.from_event(event, self.pre_event_delay, current_game_time)
        self._events.append(buffered)
        while len(self._events) > self.max_size:
            self._events.popleft()
        return buffered

    def events_for_player(self, player: str) -> list[GameEvent]:
        return [b.event for b in self._events if b.event.player == player]

    def events_in_range(self, start: float, end: float) -> list[BufferedEvent]:
        return [b for b in self._events if start <= b.event.time <= end]

    def last(self) -> BufferedEvent | None:
        return self._events[-1] if self._events else None

    def all_events(self) -> list[GameEvent]:
        return [b.event for b in self._events]

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)
