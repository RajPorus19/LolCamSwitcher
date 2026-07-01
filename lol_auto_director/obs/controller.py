"""OBS WebSocket v5 scene controller."""

from __future__ import annotations

import logging
from typing import Callable

from lol_auto_director.config import SCENE_PLAYER_A, SCENE_PLAYER_B, SCENE_SPLIT
from lol_auto_director.director.priority import FocusTarget

logger = logging.getLogger(__name__)

try:
    import obsws_python as obs
except ImportError:
    obs = None  # type: ignore[assignment]


class OBSController:
    """
    Controls OBS scenes via WebSocket v5.

    Scene names: PLAYER_A, PLAYER_B, SPLIT
    """

    SCENE_MAP = {
        FocusTarget.PLAYER_A: SCENE_PLAYER_A,
        FocusTarget.PLAYER_B: SCENE_PLAYER_B,
        FocusTarget.SPLIT_SCREEN: SCENE_SPLIT,
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4455,
        password: str = "",
        scene_map: dict[FocusTarget, str] | None = None,
        on_scene_changed: Callable[[str], None] | None = None,
    ):
        self.host = host
        self.port = port
        self.password = password
        self.scene_map = scene_map or dict(self.SCENE_MAP)
        self.on_scene_changed = on_scene_changed
        self._client: obs.ReqClient | None = None
        self._connected = False
        self._current_scene: str | None = None

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def current_scene(self) -> str | None:
        return self._current_scene

    def connect(self) -> bool:
        if obs is None:
            logger.error("obsws-python not installed")
            return False
        try:
            self._client = obs.ReqClient(
                host=self.host,
                port=self.port,
                password=self.password,
                timeout=3,
            )
            self._connected = True
            logger.info("Connected to OBS at %s:%d", self.host, self.port)
            return True
        except Exception as exc:
            logger.error("OBS connection failed: %s", exc)
            self._connected = False
            return False

    def disconnect(self) -> None:
        self._client = None
        self._connected = False

    def switch_scene(self, scene_name: str) -> bool:
        """Switch to a named OBS scene."""
        if not self._connected or self._client is None:
            logger.warning("OBS not connected — cannot switch to %s", scene_name)
            return False
        try:
            self._client.set_current_program_scene(scene_name)
            self._current_scene = scene_name
            logger.info("OBS scene → %s", scene_name)
            if self.on_scene_changed:
                self.on_scene_changed(scene_name)
            return True
        except Exception as exc:
            logger.error("Scene switch failed (%s): %s", scene_name, exc)
            return False

    def switch_focus(self, target: FocusTarget) -> bool:
        scene = self.scene_map.get(target)
        if scene is None:
            logger.error("Unknown focus target: %s", target)
            return False
        return self.switch_scene(scene)

    def switch_player_a(self) -> bool:
        return self.switch_scene(self.scene_map[FocusTarget.PLAYER_A])

    def switch_player_b(self) -> bool:
        return self.switch_scene(self.scene_map[FocusTarget.PLAYER_B])

    def switch_split(self) -> bool:
        return self.switch_scene(self.scene_map[FocusTarget.SPLIT_SCREEN])

    def get_scenes(self) -> list[str]:
        if not self._connected or self._client is None:
            return []
        try:
            resp = self._client.get_scene_list()
            return [s["sceneName"] for s in resp.scenes]
        except Exception as exc:
            logger.error("Failed to list scenes: %s", exc)
            return []
