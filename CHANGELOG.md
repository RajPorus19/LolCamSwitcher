# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.4.0] - 2026-07-01

### Added

- **Docker Compose** stack for Linux VPS: `director` + `nginx-rtmp` + `Caddy`
- Optional OBS headless container (`docker compose --profile full`)
- Server env config: `OBS_ENABLED`, `REQUIRE_API_TOKEN`, `LOGS_DIR`
- `--no-obs` CLI flag for API-only server mode
- **Windows client-only** build: `build-client.spec` → `LoLAutoDirectorClient.exe`
- [docker/DOCKER.md](docker/DOCKER.md) deployment guide

## [1.3.0] - 2026-07-01

### Added

- **Client agent** (`client_main.py`) — standalone live events + optional relay to server
- **Regie server** (`server_main.py`) — FastAPI, Bearer token auth, OBS director on VPS
- `RemoteEventHub` aggregates events from remote clients
- API: `POST /api/v1/events`, `POST /api/v1/heartbeat`, `GET /api/v1/status`

## [1.2.0] - 2026-07-01

### Added

- Per-game session logs (`game_YYYY-MM-DD_HHMMSS.log`) with events, focus decisions, and camera switches
- Live log viewer in GUI with past log file picker and open-folder button
- Logs stored in `%LOCALAPPDATA%\\LoLAutoDirector\\logs` (Windows)

## [1.1.0] - 2026-07-01

### Added

- Extended `EventType` coverage: triple/quadra/penta, first blood, ace, dragon/baron/herald, turret, inhibitor
- Full Riot Live Client `eventdata` mapping including assists from `ChampionKill`
- Heuristic detection for `engage` (combat spike) and `farm` (CS spike)
- Unit tests for Riot event mapping (`tests/test_api_mapping.py`)

## [1.0.0] - 2026-07-01

### Added

- LoL Auto Director GUI (PySide6) for Windows
- Riot Live Client Data API integration (Vanguard-safe, no memory access)
- OBS WebSocket v5 scene switching (`PLAYER_A`, `PLAYER_B`, `SPLIT`)
- Event buffer with configurable pre-event delay (instant replay offset)
- Switch strategies: score-based, one main player, dual alternation
- Interest scoring with decay (kill, objective, engage, etc.)
- Split screen on simultaneous major events
- Setup guide for two remote POV streams ([README.md](README.md))
- Live event testing guide ([TESTING.md](TESTING.md))
- CLI probe script `scripts/test_live_events.py`
- Windows `.exe` build via PyInstaller (`build.bat`, GitHub Actions release)

[1.4.0]: https://github.com/RajPorus19/LolCamSwitcher/releases/tag/v1.4.0
[1.3.0]: https://github.com/RajPorus19/LolCamSwitcher/releases/tag/v1.3.0
[1.2.0]: https://github.com/RajPorus19/LolCamSwitcher/releases/tag/v1.2.0
[1.1.0]: https://github.com/RajPorus19/LolCamSwitcher/releases/tag/v1.1.0
[1.0.0]: https://github.com/RajPorus19/LolCamSwitcher/releases/tag/v1.0.0
