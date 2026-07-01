"""Refactored director engine with pluggable event source."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from lol_auto_director.buffer.recorder import ReplayRecorder
from lol_auto_director.common.event_source import EventSource
from lol_auto_director.config import AppConfig
from lol_auto_director.director.priority import FocusTarget
from lol_auto_director.director.strategy import SwitchStrategy
from lol_auto_director.lol.api import RiotLiveClientAPI
from lol_auto_director.lol.events import EventType, GameEvent
from lol_auto_director.obs.controller import OBSController
from lol_auto_director.session_log.game_logger import GameSessionLogger, default_logs_dir

logger = logging.getLogger(__name__)


@dataclass
class DirectorEngine:
    """Background engine polling an event source and driving OBS scene switches."""

    config: AppConfig = field(default_factory=AppConfig)
    event_source: EventSource | None = None
    on_state_changed: Callable[[], None] | None = None
    on_log_line: Callable[[str], None] | None = None
    enable_obs: bool = True

    recorder: ReplayRecorder = field(init=False)
    source: EventSource = field(init=False)
    obs: OBSController = field(init=False)
    game_log: GameSessionLogger = field(init=False)

    _thread: threading.Thread | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _last_focus: FocusTarget | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        logs_path = Path(self.config.logs_dir) if self.config.logs_dir else default_logs_dir()
        self.game_log = GameSessionLogger(logs_dir=logs_path, on_line=self.on_log_line)
        self.recorder = ReplayRecorder(
            pre_event_delay=self.config.pre_event_delay,
            post_event_focus=self.config.min_focus_time,
        )
        self.recorder.director.min_focus_time = self.config.min_focus_time
        self.recorder.director.scoreboard.decay_factor = self.config.score_decay_factor
        self.recorder.director.switch_strategy = self.config.switch_strategy
        self.recorder.director.main_player = self.config.main_player
        self.recorder.director.strategy_state.main_player = self.config.main_player
        self.recorder.director.split_screen_enabled = self.config.split_screen_enabled

        if self.event_source is not None:
            self.source = self.event_source
        else:
            self.source = RiotLiveClientAPI(
                base_url=self.config.riot_live_client_url,
                player_a_name=self.config.player_a.summoner_name,
                player_b_name=self.config.player_b.summoner_name,
            )

        self.obs = OBSController(
            host=self.config.obs_host,
            port=self.config.obs_port,
            password=self.config.obs_password,
            scene_map={
                FocusTarget.PLAYER_A: self.config.player_a.scene_name,
                FocusTarget.PLAYER_B: self.config.player_b.scene_name,
                FocusTarget.SPLIT_SCREEN: self.config.split_scene_name,
            },
            on_scene_changed=lambda _: self._notify(),
        )

    @property
    def logs_dir(self) -> Path:
        return self.game_log.logs_dir

    @property
    def current_log_file(self) -> Path | None:
        return self.game_log.current_log_path

    @property
    def source_connected(self) -> bool:
        return self.source.is_available()

    # Backward-compatible alias
    @property
    def riot_connected(self) -> bool:
        return self.source_connected

    def _scene_name(self, focus: FocusTarget) -> str:
        return self.obs.scene_map.get(focus, focus.value)

    def _apply_focus(
        self,
        focus: FocusTarget,
        game_time: float,
        *,
        trigger: str,
        switch_obs: bool,
    ) -> None:
        if focus != self._last_focus:
            state = self.recorder.director.state
            self.game_log.log_focus_decision(
                focus,
                game_time,
                reason=state.last_reason,
                score_a=state.score_a,
                score_b=state.score_b,
                focus_start=state.focus_start,
                focus_end=state.focus_end,
                last_event=state.last_event,
            )
            self._last_focus = focus

        if switch_obs and self.enable_obs:
            scene = self._scene_name(focus)
            if self.obs.connected:
                self.obs.switch_focus(focus)
            self.game_log.log_camera_switch(
                scene,
                focus,
                game_time,
                obs_connected=self.obs.connected,
                trigger=trigger,
            )

    @property
    def auto_mode(self) -> bool:
        return self.config.auto_mode

    @auto_mode.setter
    def auto_mode(self, value: bool) -> None:
        self.config.auto_mode = value
        self._notify()

    @property
    def current_focus(self) -> FocusTarget:
        return self.recorder.director.state.focus

    @property
    def score_a(self) -> float:
        return self.recorder.score_a

    @property
    def score_b(self) -> float:
        return self.recorder.score_b

    @property
    def last_event(self) -> GameEvent | None:
        return self.recorder.last_event

    @property
    def game_time(self) -> float:
        return self.recorder.director.state.game_time

    @property
    def obs_connected(self) -> bool:
        return self.obs.connected

    @property
    def focus_start(self) -> float:
        return self.recorder.director.state.focus_start

    @property
    def focus_end(self) -> float:
        return self.recorder.director.state.focus_end

    @property
    def last_reason(self) -> str:
        return self.recorder.director.state.last_reason

    @property
    def debug_mode(self) -> bool:
        return self.config.debug_mode

    @debug_mode.setter
    def debug_mode(self, value: bool) -> None:
        self.config.debug_mode = value
        self._notify()

    @property
    def switch_strategy(self) -> SwitchStrategy:
        return self.config.switch_strategy

    @property
    def pre_event_delay(self) -> float:
        return self.config.pre_event_delay

    def apply_settings(
        self,
        *,
        pre_event_delay: float | None = None,
        switch_strategy: SwitchStrategy | None = None,
        main_player: str | None = None,
        split_screen_enabled: bool | None = None,
    ) -> None:
        if pre_event_delay is not None:
            self.config.pre_event_delay = max(0.0, pre_event_delay)
            self.recorder.set_pre_event_delay(self.config.pre_event_delay)
        if switch_strategy is not None:
            self.config.switch_strategy = switch_strategy
        if main_player is not None:
            self.config.main_player = main_player
        if split_screen_enabled is not None:
            self.config.split_screen_enabled = split_screen_enabled
            self.recorder.director.split_screen_enabled = split_screen_enabled
        if switch_strategy is not None or main_player is not None:
            self.recorder.set_strategy(
                self.config.switch_strategy,
                self.config.main_player,
            )
        self._notify()

    def connect_obs(self) -> bool:
        if not self.enable_obs:
            return False
        ok = self.obs.connect()
        if ok:
            self.game_log.log_info("OBS WebSocket connected", self.game_time)
        return ok

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._last_focus = None
        self.game_log.log_info("Director engine started")
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DirectorEngine")
        self._thread.start()
        logger.info("Director engine started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        self.game_log.end_session(reason="engine stopped")
        self.source.close()
        if self.enable_obs:
            self.obs.disconnect()
        self._last_focus = None
        logger.info("Director engine stopped")

    def replay_last_event(self) -> None:
        decision = self.recorder.replay_last()
        if decision is None:
            logger.warning("No event to replay")
            return
        gt = decision.event.time
        self.game_log.log_info(
            f"Replay last event: {decision.event} → {decision.target.value}", gt
        )
        self._apply_focus(decision.target, gt, trigger="replay", switch_obs=True)
        self._notify()

    def manual_switch(self, target: FocusTarget) -> None:
        gt = self.game_time
        self._apply_focus(target, gt, trigger="manual", switch_obs=True)
        self._notify()

    def inject_test_event(
        self, event_type: EventType, player: str, game_time: float | None = None
    ) -> None:
        t = game_time if game_time is not None else self.game_time or 600.0
        event = GameEvent(event_type, player, t)
        with self._lock:
            decision = self.recorder.record_event(event, t)
            state = self.recorder.get_focus_at(t)
        self.game_log.log_event(event, decision, t)
        if self.config.debug_mode:
            self.game_log.log_director_decision(
                event,
                state,
                decision,
                t,
            )
        self.game_log.log_info(f"Test event injected: {event_type.value} ({player})", t)
        self._apply_focus(
            state.focus,
            t,
            trigger="test",
            switch_obs=self.config.auto_mode,
        )
        self._notify()

    def process_external_event(self, event: GameEvent) -> None:
        """Ingest a single event (e.g. from HTTP API on server)."""
        with self._lock:
            decision = self.recorder.record_event(event, event.time)
            state = self.recorder.get_focus_at(event.time)
        self.game_log.log_event(event, decision, event.time)
        if self.config.debug_mode:
            self.game_log.log_director_decision(
                event,
                state,
                decision,
                event.time,
            )
        if state.focus != self._last_focus:
            self._apply_focus(
                state.focus,
                event.time,
                trigger="remote",
                switch_obs=self.config.auto_mode,
            )
        self._notify()

    def _loop(self) -> None:
        interval = self.config.riot_poll_interval_ms / 1000.0
        while self._running:
            try:
                self._tick()
            except Exception:
                logger.exception("Engine tick error")
            time.sleep(interval)

    def _tick(self) -> None:
        available = self.source.is_available()
        game_time = self.source.get_game_time() if available else self.game_time
        self.game_log.tick(available, game_time)

        if not available:
            return

        new_events = self.source.poll_events()

        with self._lock:
            for event in new_events:
                decision = self.recorder.record_event(event, game_time)
                self.game_log.log_event(event, decision, game_time)
            state = self.recorder.get_focus_at(game_time)
            if self.config.debug_mode:
                for event in new_events:
                    decision = next(
                        (
                            d
                            for d in reversed(self.recorder.director.pending_decisions)
                            if d.event is event
                        ),
                        None,
                    )
                    if decision:
                        self.game_log.log_director_decision(
                            event, state, decision, game_time
                        )

        if state.focus != self._last_focus:
            self._apply_focus(
                state.focus,
                game_time,
                trigger="timeline" if not new_events else "event",
                switch_obs=self.config.auto_mode,
            )

        self._notify()

    def _notify(self) -> None:
        if self.on_state_changed:
            self.on_state_changed()
