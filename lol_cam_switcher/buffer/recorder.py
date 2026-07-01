"""Recorder bridge — connects event buffer to director timeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from lol_cam_switcher.buffer.timeline import EventBuffer
from lol_cam_switcher.director.timeline import DirectorTimeline, FocusDecision
from lol_cam_switcher.lol.events import GameEvent

logger = logging.getLogger(__name__)


@dataclass
class ReplayRecorder:
    """
    Coordinates the event buffer and director timeline.

    Implements instant replay: events are buffered, decisions use target_time offset.
    """

    pre_event_delay: float = 3.0
    post_event_focus: float = 12.0
    buffer: EventBuffer = field(default_factory=EventBuffer)
    director: DirectorTimeline = field(default_factory=DirectorTimeline)

    def __post_init__(self) -> None:
        self._sync_director_settings()

    def _sync_director_settings(self) -> None:
        self.buffer.pre_event_delay = self.pre_event_delay
        self.director.pre_event_delay = self.pre_event_delay
        self.director.post_event_focus = self.post_event_focus

    def set_pre_event_delay(self, delay: float) -> None:
        self.pre_event_delay = max(0.0, delay)
        self.buffer.pre_event_delay = self.pre_event_delay
        self.director.set_pre_event_delay(delay)

    def set_strategy(self, strategy, main_player: str = "A") -> None:
        self.director.set_strategy(strategy, main_player)

    def record_event(self, event: GameEvent, current_game_time: float) -> FocusDecision:
        """Buffer event and produce a focus decision."""
        buffered = self.buffer.push(event, current_game_time)
        decision = self.director.add_event(event)
        logger.info(
            "Event buffered: %s → target_time=%.1fs (offset -%.0fs)",
            event,
            buffered.target_time,
            self.pre_event_delay,
        )
        return decision

    def get_focus_at(self, game_time: float):
        return self.director.evaluate(game_time)

    def replay_last(self) -> FocusDecision | None:
        return self.director.replay_last_event()

    def reset(self) -> None:
        self.buffer.clear()
        self.director.reset()

    @property
    def last_event(self) -> GameEvent | None:
        last = self.buffer.last()
        return last.event if last else None

    @property
    def score_a(self) -> float:
        return self.director.scoreboard.player_a.interest_score

    @property
    def score_b(self) -> float:
        return self.director.scoreboard.player_b.interest_score
