"""Switch strategies for camera focus decisions."""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from lol_cam_switcher.director.priority import FocusTarget, choose_focus, detect_split_screen
from lol_cam_switcher.lol.events import GameEvent


class SwitchStrategy(str, Enum):
    """Camera switching strategy."""

    SCORE_BASED = "score_based"
    ONE_MAIN_PLAYER = "one_main_player"
    DUAL_PLAYER = "dual_player"


STRATEGY_LABELS: dict[SwitchStrategy, str] = {
    SwitchStrategy.SCORE_BASED: "Score (priorité auto)",
    SwitchStrategy.ONE_MAIN_PLAYER: "Joueur principal",
    SwitchStrategy.DUAL_PLAYER: "Dual (alternance)",
}


def player_to_focus(player_id: str) -> FocusTarget:
    return FocusTarget.PLAYER_A if player_id == "A" else FocusTarget.PLAYER_B


@dataclass
class StrategyState:
    """Runtime state for strategy-specific switching logic."""

    strategy: SwitchStrategy = SwitchStrategy.SCORE_BASED
    main_player: str = "A"
    locked_player: str = "A"
    initialized: bool = False

    def reset(self, strategy: SwitchStrategy | None = None) -> None:
        if strategy is not None:
            self.strategy = strategy
        self.main_player = "A"
        self.locked_player = "A"
        self.initialized = False

    def init_dual_player(self) -> FocusTarget:
        """Pick a random starting player for dual strategy."""
        if not self.initialized:
            self.locked_player = random.choice(["A", "B"])
            self.initialized = True
        return player_to_focus(self.locked_player)


def _check_split_screen(
    player_a_events: list[GameEvent],
    player_b_events: list[GameEvent],
    current_time: float,
    major_event_window: float,
    *,
    split_screen_enabled: bool = False,
) -> FocusTarget | None:
    if not split_screen_enabled:
        return None
    recent_a = [e for e in player_a_events if current_time - e.time <= major_event_window]
    recent_b = [e for e in player_b_events if current_time - e.time <= major_event_window]
    if detect_split_screen(recent_a, recent_b, major_event_window):
        return FocusTarget.SPLIT_SCREEN
    return None


def resolve_focus_for_event(
    strategy: SwitchStrategy,
    strategy_state: StrategyState,
    event: GameEvent,
    player_a_events: list[GameEvent],
    player_b_events: list[GameEvent],
    score_a: float,
    score_b: float,
    major_event_window: float,
    *,
    split_screen_enabled: bool = False,
) -> FocusTarget:
    """
    Decide focus target when a new event arrives.

    ONE_MAIN_PLAYER: stay on main player; switch to secondary only on their action.
    DUAL_PLAYER: switch to whoever acted; stay until the other player acts.
    SCORE_BASED: score + priority clash resolution.
    """
    split = _check_split_screen(
        player_a_events,
        player_b_events,
        event.time,
        major_event_window,
        split_screen_enabled=split_screen_enabled,
    )
    if split is not None:
        return split

    if strategy == SwitchStrategy.SCORE_BASED:
        return choose_focus(
            player_a_events,
            player_b_events,
            score_a,
            score_b,
            event.time,
            major_event_window,
            split_screen_enabled=split_screen_enabled,
        )

    if strategy == SwitchStrategy.ONE_MAIN_PLAYER:
        if event.player == strategy_state.main_player:
            return player_to_focus(strategy_state.main_player)
        return player_to_focus(event.player)

    if strategy == SwitchStrategy.DUAL_PLAYER:
        strategy_state.locked_player = event.player
        strategy_state.initialized = True
        return player_to_focus(event.player)

    return choose_focus(
        player_a_events,
        player_b_events,
        score_a,
        score_b,
        event.time,
        major_event_window,
        split_screen_enabled=split_screen_enabled,
    )


def resolve_idle_focus(
    strategy: SwitchStrategy,
    strategy_state: StrategyState,
    player_a_events: list[GameEvent],
    player_b_events: list[GameEvent],
    score_a: float,
    score_b: float,
    current_time: float,
    major_event_window: float,
    *,
    split_screen_enabled: bool = False,
) -> FocusTarget:
    """Decide focus when no active focus window is running."""
    split = _check_split_screen(
        player_a_events,
        player_b_events,
        current_time,
        major_event_window,
        split_screen_enabled=split_screen_enabled,
    )
    if split is not None:
        return split

    if strategy == SwitchStrategy.SCORE_BASED:
        return choose_focus(
            player_a_events,
            player_b_events,
            score_a,
            score_b,
            current_time,
            major_event_window,
            split_screen_enabled=split_screen_enabled,
        )

    if strategy == SwitchStrategy.ONE_MAIN_PLAYER:
        return player_to_focus(strategy_state.main_player)

    if strategy == SwitchStrategy.DUAL_PLAYER:
        return strategy_state.init_dual_player()

    return FocusTarget.PLAYER_A
