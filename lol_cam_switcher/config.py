"""Global configuration constants."""

from dataclasses import dataclass, field

from lol_cam_switcher.director.strategy import SwitchStrategy

# Pre-action replay offset: show action from T - PRE_EVENT_DELAY
PRE_EVENT_DELAY = 3.0
# Minimum time locked on a POV after a switch (unless critical event)
MIN_FOCUS_TIME = 10.0
# Legacy alias used by timeline focus windows
POST_EVENT_FOCUS = MIN_FOCUS_TIME
DETECTION_DELAY = 0.0
# Instant interest decay: score *= factor each second
SCORE_DECAY_FACTOR = 0.8
# Deprecated linear decay name — kept for imports that expect the symbol
SCORE_DECAY_PER_SECOND = SCORE_DECAY_FACTOR

SPLIT_SCREEN_DURATION = 8.0
MAJOR_EVENT_WINDOW = 5.0

SCENE_PLAYER_A = "PLAYER_A"
SCENE_PLAYER_B = "PLAYER_B"
SCENE_MAIN = "MAIN"
SCENE_SPLIT = "SPLIT"

RIOT_LIVE_CLIENT_URL = "https://127.0.0.1:2999"
RIOT_POLL_INTERVAL_MS = 500

OBS_HOST = "localhost"
OBS_PORT = 4455
OBS_PASSWORD = ""


@dataclass
class PlayerConfig:
    """Mapping between internal player id and Riot summoner name."""

    id: str  # "A" or "B"
    summoner_name: str = ""
    scene_name: str = ""


@dataclass
class AppConfig:
    pre_event_delay: float = PRE_EVENT_DELAY
    min_focus_time: float = MIN_FOCUS_TIME
    post_event_focus: float = POST_EVENT_FOCUS
    detection_delay: float = DETECTION_DELAY
    split_screen_duration: float = SPLIT_SCREEN_DURATION
    major_event_window: float = MAJOR_EVENT_WINDOW
    score_decay_factor: float = SCORE_DECAY_FACTOR
    riot_live_client_url: str = RIOT_LIVE_CLIENT_URL
    riot_poll_interval_ms: int = RIOT_POLL_INTERVAL_MS
    obs_host: str = OBS_HOST
    obs_port: int = OBS_PORT
    obs_password: str = OBS_PASSWORD
    player_a: PlayerConfig = field(
        default_factory=lambda: PlayerConfig(id="A", scene_name=SCENE_PLAYER_A)
    )
    player_b: PlayerConfig = field(
        default_factory=lambda: PlayerConfig(id="B", scene_name=SCENE_PLAYER_B)
    )
    main_scene_name: str = SCENE_MAIN
    split_scene_name: str = SCENE_SPLIT
    split_screen_enabled: bool = False
    auto_mode: bool = True
    debug_mode: bool = False
    switch_strategy: SwitchStrategy = SwitchStrategy.SCORE_BASED
    main_player: str = "A"
    logs_dir: str = ""  # empty = default (AppData/LolCamSwitcher/logs)
