"""FastAPI regie server — receives events from clients, runs director + OBS."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lol_auto_director.common.schemas import (
    EventPayload,
    HeartbeatPayload,
    IngestResponse,
    StatusResponse,
)
from lol_auto_director.config import AppConfig
from lol_auto_director.engine import DirectorEngine
from lol_auto_director.server.auth import make_verify_token
from lol_auto_director.server.config import ServerConfig, app_config_from_env
from lol_auto_director.server.hub import RemoteEventHub

logger = logging.getLogger(__name__)

_hub: RemoteEventHub | None = None
_engine: DirectorEngine | None = None
_server_config: ServerConfig | None = None


def get_hub() -> RemoteEventHub:
    assert _hub is not None
    return _hub


def get_engine() -> DirectorEngine:
    assert _engine is not None
    return _engine


def create_app(server_config: ServerConfig | None = None, app_config: AppConfig | None = None) -> FastAPI:
    global _hub, _engine, _server_config

    _server_config = server_config or ServerConfig()
    token = _server_config.ensure_token()
    verify = make_verify_token(token)
    _hub = RemoteEventHub()
    obs_enabled = _server_config.obs_enabled

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        global _engine
        cfg = app_config or app_config_from_env()
        _engine = DirectorEngine(config=cfg, event_source=_hub, enable_obs=obs_enabled)
        _engine.start()
        if obs_enabled:
            if _engine.connect_obs():
                logger.info("OBS connected on server startup")
            else:
                logger.warning(
                    "OBS not connected — set OBS_HOST/OBS_PASSWORD or use OBS_ENABLED=false"
                )
        else:
            logger.info("OBS disabled (OBS_ENABLED=false) — API + event regie only")
        logger.info("Regie server started — API token required for /api/v1/*")
        if not _server_config.require_token:
            logger.info("API token: %s", token)
        yield
        _engine.stop()
        _engine = None

    app = FastAPI(
        title="LoL Auto Director Server",
        description="Central regie API — ingest events from client agents, control OBS",
        version="1.4.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_server_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict:
        eng = get_engine()
        hub = get_hub()
        return {
            "status": "ok",
            "obs_enabled": obs_enabled,
            "obs_connected": eng.obs_connected if obs_enabled else None,
            "clients": hub.connected_clients(),
        }

    @app.get("/api/v1/status", response_model=StatusResponse, dependencies=[Depends(verify)])
    def status() -> StatusResponse:
        eng = get_engine()
        hub = get_hub()
        last = eng.last_event
        return StatusResponse(
            game_time=eng.game_time,
            focus=eng.current_focus.value,
            score_a=eng.score_a,
            score_b=eng.score_b,
            last_event=str(last) if last else None,
            clients_connected=hub.connected_clients(),
            obs_connected=eng.obs_connected if obs_enabled else False,
            auto_mode=eng.auto_mode,
        )

    @app.post("/api/v1/events", response_model=IngestResponse, dependencies=[Depends(verify)])
    def ingest_event(payload: EventPayload) -> IngestResponse:
        hub = get_hub()
        try:
            hub.ingest_event(
                payload.player,
                payload.type,
                payload.time,
                payload.summoner_name,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return IngestResponse(accepted=True, message=f"Event {payload.type} for {payload.player}")

    @app.post("/api/v1/heartbeat", response_model=IngestResponse, dependencies=[Depends(verify)])
    def heartbeat(payload: HeartbeatPayload) -> IngestResponse:
        get_hub().ingest_heartbeat(
            payload.player,
            payload.game_time,
            payload.summoner_name,
            payload.lol_connected,
        )
        return IngestResponse(accepted=True)

    return app
