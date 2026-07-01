"""Unit tests for director logic."""

import pytest

from lol_auto_director.director.priority import FocusTarget, choose_focus, detect_split_screen
from lol_auto_director.director.scoring import ScoreBoard
from lol_auto_director.director.strategy import (
    SwitchStrategy,
    resolve_focus_for_event,
    resolve_idle_focus,
    StrategyState,
)
from lol_auto_director.director.timeline import DirectorTimeline, FocusDecision
from lol_auto_director.lol.events import EventType, GameEvent


def _event(type_: EventType, player: str, time: float) -> GameEvent:
    return GameEvent(type_, player, time)


class TestFocusDecision:
    def test_pre_event_offset(self):
        event = _event(EventType.KILL, "A", 1200.0)  # 20:00
        decision = FocusDecision.from_event(event)
        assert decision.start_time == pytest.approx(1197.0)  # 19:57
        assert decision.end_time == pytest.approx(1207.0)  # 19:57 + 10s lock
        assert decision.target == FocusTarget.PLAYER_A
        assert decision.reason == "KILL"

    def test_solo_kill_reason(self):
        event = _event(EventType.SOLO_KILL, "A", 630.0)
        decision = FocusDecision.from_event(event)
        assert decision.reason == "SOLO KILL"
        assert decision.bypass_lock is False


class TestScoring:
    def test_kill_adds_100(self):
        board = ScoreBoard()
        board.apply_event(_event(EventType.KILL, "A", 100.0))
        assert board.player_a.interest_score == 100

    def test_solo_kill_adds_120(self):
        board = ScoreBoard()
        board.apply_event(_event(EventType.SOLO_KILL, "A", 100.0))
        assert board.player_a.interest_score == 120

    def test_exponential_decay(self):
        board = ScoreBoard(decay_factor=0.8)
        board.apply_event(_event(EventType.KILL, "A", 100.0))
        score, _ = board.scores_at(101.0)
        assert score == pytest.approx(80.0)


class TestChooseFocus:
    def test_kill_wins_over_engage(self):
        events_a = [_event(EventType.ENGAGE, "A", 50.0)]
        events_b = [_event(EventType.KILL, "B", 52.0)]
        result = choose_focus(events_a, events_b, 60, 100, 52.0)
        assert result == FocusTarget.PLAYER_B

    def test_split_on_simultaneous_kills_when_enabled(self):
        events_a = [_event(EventType.KILL, "A", 100.0)]
        events_b = [_event(EventType.KILL, "B", 103.0)]
        assert detect_split_screen(events_a, events_b, window=5.0)
        result = choose_focus(
            events_a, events_b, 100, 100, 103.0, split_screen_enabled=True
        )
        assert result == FocusTarget.SPLIT_SCREEN

    def test_split_disabled_picks_pov(self):
        events_a = [_event(EventType.KILL, "A", 100.0)]
        events_b = [_event(EventType.KILL, "B", 103.0)]
        result = choose_focus(events_a, events_b, 100, 100, 103.0)
        assert result in (FocusTarget.PLAYER_A, FocusTarget.PLAYER_B)
        assert result != FocusTarget.SPLIT_SCREEN


class TestDirectorTimeline:
    def test_evaluate_focus_window(self):
        director = DirectorTimeline()
        event = _event(EventType.KILL, "A", 1200.0)
        director.add_event(event)

        state = director.evaluate(1197.0)
        assert state.focus == FocusTarget.PLAYER_A
        assert state.last_reason == "KILL"

        state = director.evaluate(1205.0)
        assert state.focus == FocusTarget.PLAYER_A

        state = director.evaluate(1210.0)
        assert state.focus == FocusTarget.PLAYER_A  # score still favors A

    def test_custom_pre_event_delay(self):
        director = DirectorTimeline(pre_event_delay=5.0)
        event = _event(EventType.KILL, "A", 100.0)
        director.add_event(event)
        state = director.evaluate(95.0)
        assert state.focus == FocusTarget.PLAYER_A
        assert state.pre_event_delay == 5.0

    def test_focus_lock_blocks_early_switch(self):
        director = DirectorTimeline(pre_event_delay=3.0, min_focus_time=10.0)
        director.add_event(_event(EventType.KILL, "A", 100.0))
        director.evaluate(100.0)
        director.add_event(_event(EventType.KILL, "B", 105.0))
        state = director.evaluate(105.0)
        assert state.focus == FocusTarget.PLAYER_A

    def test_critical_event_bypasses_focus_lock(self):
        director = DirectorTimeline(pre_event_delay=3.0, min_focus_time=10.0)
        director.add_event(_event(EventType.KILL, "A", 100.0))
        director.evaluate(100.0)
        director.add_event(_event(EventType.PENTA_KILL, "B", 105.0))
        state = director.evaluate(105.0)
        assert state.focus == FocusTarget.PLAYER_B
        assert state.last_reason == "PENTAKILL"

    def test_replay_last(self):
        director = DirectorTimeline()
        event = _event(EventType.KILL, "B", 900.0)
        director.add_event(event)
        replay = director.replay_last_event()
        assert replay is not None
        assert replay.event == event
        assert replay.start_time == pytest.approx(897.0)


class TestSwitchStrategies:
    def test_one_main_player_switches_on_b_action(self):
        state = StrategyState(strategy=SwitchStrategy.ONE_MAIN_PLAYER, main_player="A")
        event = _event(EventType.KILL, "B", 100.0)
        target = resolve_focus_for_event(
            SwitchStrategy.ONE_MAIN_PLAYER,
            state,
            event,
            [],
            [event],
            0,
            100,
            5.0,
        )
        assert target == FocusTarget.PLAYER_B

    def test_one_main_player_returns_to_main_when_idle(self):
        state = StrategyState(strategy=SwitchStrategy.ONE_MAIN_PLAYER, main_player="A")
        idle = resolve_idle_focus(
            SwitchStrategy.ONE_MAIN_PLAYER,
            state,
            [],
            [],
            0,
            100,
            200.0,
            5.0,
        )
        assert idle == FocusTarget.PLAYER_A

    def test_dual_player_alternates(self):
        state = StrategyState(strategy=SwitchStrategy.DUAL_PLAYER, locked_player="A")
        state.initialized = True

        event_b = _event(EventType.KILL, "B", 100.0)
        target = resolve_focus_for_event(
            SwitchStrategy.DUAL_PLAYER, state, event_b, [], [event_b], 0, 100, 5.0
        )
        assert target == FocusTarget.PLAYER_B

        event_a = _event(EventType.KILL, "A", 120.0)
        target = resolve_focus_for_event(
            SwitchStrategy.DUAL_PLAYER, state, event_a, [event_a], [event_b], 100, 100, 5.0
        )
        assert target == FocusTarget.PLAYER_A

    def test_one_main_timeline_b_then_back_to_a(self):
        director = DirectorTimeline(
            switch_strategy=SwitchStrategy.ONE_MAIN_PLAYER,
            main_player="A",
            pre_event_delay=3.0,
            min_focus_time=10.0,
        )
        director.add_event(_event(EventType.KILL, "B", 100.0))
        assert director.evaluate(100.0).focus == FocusTarget.PLAYER_B
        assert director.evaluate(115.0).focus == FocusTarget.PLAYER_A
