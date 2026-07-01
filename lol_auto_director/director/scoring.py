"""Player interest scoring with time decay."""

from __future__ import annotations

from dataclasses import dataclass, field

from lol_auto_director.config import SCORE_DECAY_PER_SECOND
from lol_auto_director.lol.events import EVENT_SCORES, EventType, GameEvent


@dataclass
class PlayerScore:
    """Accumulated interest score for one player."""

    player_id: str
    interest_score: float = 0.0
    last_update_time: float = 0.0

    def apply_decay(self, current_time: float, decay_rate: float = SCORE_DECAY_PER_SECOND) -> None:
        if self.last_update_time <= 0:
            self.last_update_time = current_time
            return
        elapsed = max(0.0, current_time - self.last_update_time)
        self.interest_score = max(0.0, self.interest_score - decay_rate * elapsed)
        self.last_update_time = current_time

    def add_event(self, event: GameEvent, current_time: float) -> None:
        self.apply_decay(current_time)
        self.interest_score += EVENT_SCORES.get(event.type, 0)
        self.last_update_time = current_time

    def reset(self) -> None:
        self.interest_score = 0.0
        self.last_update_time = 0.0


@dataclass
class ScoreBoard:
    """Tracks interest scores for both players."""

    player_a: PlayerScore = field(default_factory=lambda: PlayerScore("A"))
    player_b: PlayerScore = field(default_factory=lambda: PlayerScore("B"))
    decay_rate: float = SCORE_DECAY_PER_SECOND

    def get(self, player_id: str) -> PlayerScore:
        return self.player_a if player_id == "A" else self.player_b

    def apply_event(self, event: GameEvent) -> None:
        self.get(event.player).add_event(event, event.time)

    def tick(self, current_time: float) -> None:
        self.player_a.apply_decay(current_time, self.decay_rate)
        self.player_b.apply_decay(current_time, self.decay_rate)

    def scores_at(self, current_time: float) -> tuple[float, float]:
        """Return (score_a, score_b) with decay applied up to current_time."""
        a = PlayerScore("A", self.player_a.interest_score, self.player_a.last_update_time)
        b = PlayerScore("B", self.player_b.interest_score, self.player_b.last_update_time)
        a.apply_decay(current_time, self.decay_rate)
        b.apply_decay(current_time, self.decay_rate)
        return a.interest_score, b.interest_score

    def reset(self) -> None:
        self.player_a.reset()
        self.player_b.reset()
