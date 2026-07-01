"""Director timeline — focus windows with pre-event offset."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from lol_auto_director.config import (
    POST_EVENT_FOCUS,
    PRE_EVENT_DELAY,
    SPLIT_SCREEN_DURATION,
)
from lol_auto_director.director.priority import FocusTarget
from lol_auto_director.director.scoring import ScoreBoard
from lol_auto_director.director.strategy import (
    StrategyState,
    SwitchStrategy,
    resolve_focus_for_event,
    resolve_idle_focus,
)
from lol_auto_director.lol.events import GameEvent


class FocusPhase(str, Enum):
    IDLE = "idle"
    FOCUSED = "focused"
    SPLIT = "split"
    POST_SPLIT = "post_split"


@dataclass
class FocusDecision:
    """A camera decision derived from one event."""

    event: GameEvent
    target: FocusTarget
    start_time: float  # event.time - PRE_EVENT_DELAY
    end_time: float  # event.time + POST_EVENT_FOCUS
    pre_event_delay: float = PRE_EVENT_DELAY

    @classmethod
    def from_event(
        cls,
        event: GameEvent,
        target: FocusTarget | None = None,
        pre_delay: float = PRE_EVENT_DELAY,
        post_focus: float = POST_EVENT_FOCUS,
    ) -> FocusDecision:
        if target is None:
            player_target = (
                FocusTarget.PLAYER_A if event.player == "A" else FocusTarget.PLAYER_B
            )
            target = player_target
        return cls(
            event=event,
            target=target,
            start_time=event.time - pre_delay,
            end_time=event.time + post_focus,
            pre_event_delay=pre_delay,
        )

    def is_active_at(self, game_time: float) -> bool:
        return self.start_time <= game_time <= self.end_time

    def __str__(self) -> str:
        return (
            f"{self.target.value} [{self.start_time:.0f}s → {self.end_time:.0f}s] "
            f"← {self.event}"
        )


@dataclass
class SplitDecision:
    """Temporary split-screen when both players have major events."""

    start_time: float
    end_time: float
    event_a: GameEvent
    event_b: GameEvent
    post_split_target: FocusTarget = FocusTarget.PLAYER_A

    @classmethod
    def from_events(
        cls,
        event_a: GameEvent,
        event_b: GameEvent,
        score_a: float,
        score_b: float,
        duration: float = SPLIT_SCREEN_DURATION,
        pre_delay: float = PRE_EVENT_DELAY,
    ) -> SplitDecision:
        center = (event_a.time + event_b.time) / 2.0
        post_target = (
            FocusTarget.PLAYER_A if score_a >= score_b else FocusTarget.PLAYER_B
        )
        return cls(
            start_time=center - pre_delay,
            end_time=center + duration,
            event_a=event_a,
            event_b=event_b,
            post_split_target=post_target,
        )

    def is_active_at(self, game_time: float) -> bool:
        return self.start_time <= game_time <= self.end_time


@dataclass
class DirectorState:
    """Current director output state."""

    focus: FocusTarget = FocusTarget.PLAYER_A
    phase: FocusPhase = FocusPhase.IDLE
    active_decision: FocusDecision | None = None
    active_split: SplitDecision | None = None
    last_event: GameEvent | None = None
    pre_event_delay: float = PRE_EVENT_DELAY
    game_time: float = 0.0


@dataclass
class DirectorTimeline:
    """
    Manages the event buffer and produces camera decisions.

    Instant replay logic: when event arrives at T, camera shows sequence from T - 3s.
    """

    pre_event_delay: float = PRE_EVENT_DELAY
    post_event_focus: float = POST_EVENT_FOCUS
    split_duration: float = SPLIT_SCREEN_DURATION
    major_event_window: float = 5.0
    switch_strategy: SwitchStrategy = SwitchStrategy.SCORE_BASED
    main_player: str = "A"

    events_a: list[GameEvent] = field(default_factory=list)
    events_b: list[GameEvent] = field(default_factory=list)
    pending_decisions: list[FocusDecision] = field(default_factory=list)
    pending_splits: list[SplitDecision] = field(default_factory=list)
    scoreboard: ScoreBoard = field(default_factory=ScoreBoard)
    strategy_state: StrategyState = field(default_factory=StrategyState)
    state: DirectorState = field(default_factory=DirectorState)

    def add_event(self, event: GameEvent) -> FocusDecision:
        """Buffer an event and create a focus decision with pre-event offset."""
        if event.player == "A":
            self.events_a.append(event)
        else:
            self.events_b.append(event)

        self.scoreboard.apply_event(event)
        self.state.last_event = event

        score_a, score_b = self.scoreboard.scores_at(event.time)
        target = resolve_focus_for_event(
            self.switch_strategy,
            self.strategy_state,
            event,
            self.events_a,
            self.events_b,
            score_a,
            score_b,
            self.major_event_window,
        )

        if target == FocusTarget.SPLIT_SCREEN:
            self._maybe_create_split(event, score_a, score_b)

        decision_target = (
            target
            if target != FocusTarget.SPLIT_SCREEN
            else None
        )
        decision = FocusDecision.from_event(
            event,
            target=decision_target,
            pre_delay=self.pre_event_delay,
            post_focus=self.post_event_focus,
        )
        self.pending_decisions.append(decision)
        return decision

    def _maybe_create_split(
        self, trigger_event: GameEvent, score_a: float, score_b: float
    ) -> None:
        other_events = self.events_b if trigger_event.player == "A" else self.events_a
        major_other = [
            e
            for e in other_events
            if e.is_major
            and abs(e.time - trigger_event.time) <= self.major_event_window
        ]
        if not major_other:
            return
        partner = max(major_other, key=lambda e: e.time)
        if trigger_event.player == "A":
            split = SplitDecision.from_events(
                trigger_event,
                partner,
                score_a,
                score_b,
                self.split_duration,
                self.pre_event_delay,
            )
        else:
            split = SplitDecision.from_events(
                partner,
                trigger_event,
                score_a,
                score_b,
                self.split_duration,
                self.pre_event_delay,
            )
        self.pending_splits.append(split)

    def evaluate(self, game_time: float) -> DirectorState:
        """Determine current focus at `game_time` (instant replay position)."""
        self.state.game_time = game_time
        self.state.pre_event_delay = self.pre_event_delay
        self.scoreboard.tick(game_time)

        active_split = next(
            (s for s in reversed(self.pending_splits) if s.is_active_at(game_time)),
            None,
        )
        if active_split:
            self.state.focus = FocusTarget.SPLIT_SCREEN
            self.state.phase = FocusPhase.SPLIT
            self.state.active_split = active_split
            self.state.active_decision = None
            return self.state

        active = next(
            (d for d in reversed(self.pending_decisions) if d.is_active_at(game_time)),
            None,
        )
        if active:
            self.state.focus = active.target
            self.state.phase = FocusPhase.FOCUSED
            self.state.active_decision = active
            self.state.active_split = None
            return self.state

        score_a, score_b = self.scoreboard.scores_at(game_time)
        self.state.focus = resolve_idle_focus(
            self.switch_strategy,
            self.strategy_state,
            self.events_a,
            self.events_b,
            score_a,
            score_b,
            game_time,
            self.major_event_window,
        )
        self.state.phase = FocusPhase.IDLE
        self.state.active_decision = None
        self.state.active_split = None
        return self.state

    def replay_last_event(self) -> FocusDecision | None:
        """Return the focus decision for the most recent event (replay mode)."""
        if self.state.last_event is None:
            return None
        return FocusDecision.from_event(
            self.state.last_event,
            pre_delay=self.pre_event_delay,
            post_focus=self.post_event_focus,
        )

    def reset(self) -> None:
        self.events_a.clear()
        self.events_b.clear()
        self.pending_decisions.clear()
        self.pending_splits.clear()
        self.scoreboard.reset()
        self.strategy_state.reset(self.switch_strategy)
        self.strategy_state.main_player = self.main_player
        self.state = DirectorState(pre_event_delay=self.pre_event_delay)

    def set_strategy(self, strategy: SwitchStrategy, main_player: str = "A") -> None:
        self.switch_strategy = strategy
        self.main_player = main_player
        self.strategy_state.reset(strategy)
        self.strategy_state.main_player = main_player

    def set_pre_event_delay(self, delay: float) -> None:
        self.pre_event_delay = max(0.0, delay)
        self.state.pre_event_delay = self.pre_event_delay

    @property
    def events_a_recent(self) -> list[GameEvent]:
        return self.events_a

    @property
    def events_b_recent(self) -> list[GameEvent]:
        return self.events_b
