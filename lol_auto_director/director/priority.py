"""Priority and clash resolution between two players."""

from __future__ import annotations

from enum import Enum

from lol_auto_director.lol.events import GameEvent, MAJOR_EVENT_TYPES


class FocusTarget(str, Enum):
    PLAYER_A = "PLAYER_A"
    PLAYER_B = "PLAYER_B"
    SPLIT_SCREEN = "SPLIT_SCREEN"


def _events_in_window(
    events: list[GameEvent], center_time: float, window: float
) -> list[GameEvent]:
    return [e for e in events if abs(e.time - center_time) <= window]


def _has_major_event_near(
    events: list[GameEvent], reference_time: float, window: float
) -> bool:
    return any(
        e.is_major and abs(e.time - reference_time) <= window for e in events
    )


def _best_event(events: list[GameEvent]) -> GameEvent | None:
    if not events:
        return None
    return min(
        events,
        key=lambda e: (e.priority_tier, -e.score, -e.time),
    )


def detect_split_screen(
    player_a_events: list[GameEvent],
    player_b_events: list[GameEvent],
    window: float = 5.0,
) -> bool:
    """
    Return True if both players have a major event within `window` seconds of each other.
    """
    major_a = [e for e in player_a_events if e.is_major]
    major_b = [e for e in player_b_events if e.is_major]

    for event_a in major_a:
        for event_b in major_b:
            if abs(event_a.time - event_b.time) <= window:
                return True
    return False


def choose_focus(
    player_a_events: list[GameEvent],
    player_b_events: list[GameEvent],
    score_a: float,
    score_b: float,
    current_time: float,
    major_event_window: float = 5.0,
) -> FocusTarget:
    """
    Decide which POV to display based on recent events and interest scores.

    Priority order when events clash:
      1. Kill / big play
      2. Important objective
      3. Ongoing combat
      4. Engage
      5. Farm

    Special rule: simultaneous major events → SPLIT_SCREEN.
    """
    recent_a = [e for e in player_a_events if current_time - e.time <= 10.0]
    recent_b = [e for e in player_b_events if current_time - e.time <= 10.0]

    if detect_split_screen(recent_a, recent_b, major_event_window):
        return FocusTarget.SPLIT_SCREEN

    all_recent = recent_a + recent_b
    if not all_recent:
        if score_a > score_b:
            return FocusTarget.PLAYER_A
        if score_b > score_a:
            return FocusTarget.PLAYER_B
        return FocusTarget.PLAYER_A

    # Group events within 2s of each other — pick highest priority tier
    best_a = _best_event(recent_a)
    best_b = _best_event(recent_b)

    if best_a and best_b and abs(best_a.time - best_b.time) <= 2.0:
        if best_a.priority_tier < best_b.priority_tier:
            return FocusTarget.PLAYER_A
        if best_b.priority_tier < best_a.priority_tier:
            return FocusTarget.PLAYER_B
        if best_a.score > best_b.score:
            return FocusTarget.PLAYER_A
        if best_b.score > best_a.score:
            return FocusTarget.PLAYER_B
        return FocusTarget.PLAYER_A

    if best_a and (not best_b or best_a.time >= best_b.time):
        return FocusTarget.PLAYER_A
    if best_b:
        return FocusTarget.PLAYER_B

    if score_a >= score_b:
        return FocusTarget.PLAYER_A
    return FocusTarget.PLAYER_B


def resolve_clash(event_a: GameEvent | None, event_b: GameEvent | None) -> str | None:
    """Return winning player id ('A' or 'B') when two events compete."""
    if event_a is None and event_b is None:
        return None
    if event_a is None:
        return "B"
    if event_b is None:
        return "A"

    if event_a.priority_tier < event_b.priority_tier:
        return "A"
    if event_b.priority_tier < event_a.priority_tier:
        return "B"
    if event_a.score >= event_b.score:
        return "A"
    return "B"
