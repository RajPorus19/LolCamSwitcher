"""Global configuration constants."""

from dataclasses import dataclass, field

from lol_auto_director.director.strategy import SwitchStrategy


PRE_EVENT_DELAY = 3.0
POST_EVENT_FOCUS = 12.0
SPLIT_SCREEN_DURATION = 8.0
MAJOR_EVENT_WINDOW = 5.0
SCORE_DECAY_PER_SECOND = 2.0

SCENE_PLAYER_A = "PLAYER_A"
SCENE_PLAYER_B = "PLAYER_B"
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
    post_event_focus: float = POST_EVENT_FOCUS
    split_screen_duration: float = SPLIT_SCREEN_DURATION
    major_event_window: float = MAJOR_EVENT_WINDOW
    score_decay_per_second: float = SCORE_DECAY_PER_SECOND
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
    split_scene_name: str = SCENE_SPLIT
    auto_mode: bool = True
    switch_strategy: SwitchStrategy = SwitchStrategy.SCORE_BASED
    main_player: str = "A"
