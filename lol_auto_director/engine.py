"""Main orchestration engine — ties LoL API, director, and OBS together."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from lol_auto_director.buffer.recorder import ReplayRecorder
from lol_auto_director.config import AppConfig
from lol_auto_director.director.priority import FocusTarget
from lol_auto_director.director.strategy import SwitchStrategy
from lol_auto_director.lol.api import RiotLiveClientAPI
from lol_auto_director.lol.events import EventType, GameEvent
from lol_auto_director.obs.controller import OBSController

logger = logging.getLogger(__name__)


@dataclass
class DirectorEngine:
    """Background engine polling Riot API and driving OBS scene switches."""

    config: AppConfig = field(default_factory=AppConfig)
    on_state_changed: Callable[[], None] | None = None

    recorder: ReplayRecorder = field(init=False)
    riot_api: RiotLiveClientAPI = field(init=False)
    obs: OBSController = field(init=False)

    _thread: threading.Thread | None = field(default=None, repr=False)
    _running: bool = field(default=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        self.recorder = ReplayRecorder(
            pre_event_delay=self.config.pre_event_delay,
            post_event_focus=self.config.post_event_focus,
        )
        self.recorder.director.switch_strategy = self.config.switch_strategy
        self.recorder.director.main_player = self.config.main_player
        self.recorder.director.strategy_state.main_player = self.config.main_player
        self.riot_api = RiotLiveClientAPI(
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
    def riot_connected(self) -> bool:
        return self.riot_api.is_available()

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
    ) -> None:
        if pre_event_delay is not None:
            self.config.pre_event_delay = max(0.0, pre_event_delay)
            self.recorder.set_pre_event_delay(self.config.pre_event_delay)
        if switch_strategy is not None:
            self.config.switch_strategy = switch_strategy
        if main_player is not None:
            self.config.main_player = main_player
        if switch_strategy is not None or main_player is not None:
            self.recorder.set_strategy(
                self.config.switch_strategy,
                self.config.main_player,
            )
        self._notify()

    def connect_obs(self) -> bool:
        return self.obs.connect()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="DirectorEngine")
        self._thread.start()
        logger.info("Director engine started")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
        self.riot_api.close()
        self.obs.disconnect()
        logger.info("Director engine stopped")

    def replay_last_event(self) -> None:
        decision = self.recorder.replay_last()
        if decision is None:
            logger.warning("No event to replay")
            return
        if self.config.auto_mode:
            self.obs.switch_focus(decision.target)
        self._notify()

    def inject_test_event(
        self, event_type: EventType, player: str, game_time: float | None = None
    ) -> None:
        """Inject a synthetic event for testing without a live game."""
        t = game_time if game_time is not None else self.game_time or 600.0
        event = GameEvent(event_type, player, t)
        with self._lock:
            self.recorder.record_event(event, t)
            state = self.recorder.get_focus_at(t)
        if self.config.auto_mode:
            self.obs.switch_focus(state.focus)
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
        if not self.riot_api.is_available():
            return

        game_time = self.riot_api.get_game_time()
        new_events = self.riot_api.poll_events()

        with self._lock:
            for event in new_events:
                self.recorder.record_event(event, game_time)
            state = self.recorder.get_focus_at(game_time)

        if self.config.auto_mode and new_events:
            self.obs.switch_focus(state.focus)

        self._notify()

    def _notify(self) -> None:
        if self.on_state_changed:
            self.on_state_changed()
