# Déploiement Docker — serveur Linux (VPS)

Stack de production pour la **régie centrale**.

> **Guide pas-à-pas** (token, OBS joueur, fiches A/B) : **[SETUP.md](SETUP.md)**  
> Les **clients Windows** (`LolCamSwitcherClient.exe`) tournent sur les PC joueurs.  
> Ce compose **ne contient pas** le client — uniquement le serveur.

## Architecture Docker

```
                         Internet
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   Joueurs OBS         Clients .exe         Twitch
   RTMP :1935          HTTPS :80/443
        │                   │
        ▼                   ▼
┌───────────────────────────────────────────────────┐
│                  docker compose                    │
│                                                   │
│  ┌──────────┐         ┌─────────────┐            │
│  │  nginx   │         │    Caddy    │            │
│  │  RTMP    │         │  reverse    │            │
│  │  :1935   │         │  proxy :80  │            │
│  └────┬─────┘         └──────┬──────┘            │
│       │                      │                    │
│       │ rtmp://rtmp/live/    POST /api/v1/events  │
│       │ playerA | playerB    Bearer token         │
│       ▼                      ▼                    │
│  ┌──────────┐         ┌─────────────┐            │
│  │   OBS    │◄────────│  director   │            │
│  │  régie   │  WS v5  │  (Python)   │            │
│  │  :4455   │         │  :8750      │            │
│  └────┬─────┘         └─────────────┘            │
│       │ profile: full (optionnel)                 │
└───────┼───────────────────────────────────────────┘
        ▼
   Twitch / YouTube
```

| Service | Image / build | Rôle |
|---------|---------------|------|
| **director** | `docker/director/Dockerfile` | API régie + logs |
| **rtmp** | `alfg/nginx-rtmp` | Ingest flux OBS joueurs |
| **caddy** | `caddy:2-alpine` | Proxy HTTP(S) API |
| **obs** | `docker/obs/Dockerfile` | Optionnel — switch + stream |

## Démarrage rapide

```bash
cp .env.example .env
# Éditer .env — OBLIGATOIRE : LOL_DIRECTOR_API_TOKEN

docker compose up -d
```

Vérifier :

```bash
curl http://localhost/health
curl -H "Authorization: Bearer VOTRE_TOKEN" http://localhost/api/v1/status
```

## Flux complets

### Events (HTTP)

```
LolCamSwitcherClient.exe (Windows)
  → POST https://VPS/api/v1/events
  → Authorization: Bearer TOKEN
  → director → régie → OBS switch (si OBS_ENABLED=true)
```

### Vidéo (RTMP)

```
OBS joueur A → rtmp://VPS:1935/live/playerA
OBS joueur B → rtmp://VPS:1935/live/playerB
OBS régie    ← rtmp://rtmp:1935/live/playerA|B (réseau Docker)
```

## Ports firewall VPS

| Port | Service | Public |
|------|---------|--------|
| 1935/tcp | RTMP ingest | Oui |
| 80, 443 | API clients (Caddy) | Oui |
| 8080 | HLS preview (optionnel) | Optionnel |
| 8750 | Director (interne) | Non |
| 4455 | OBS WebSocket | Non |

## Configuration joueurs

### Client Windows

| Champ | Joueur A | Joueur B |
|-------|----------|----------|
| Slot | A | B |
| URL | `http://VPS` ou `https://domaine` | idem |
| Token | `LOL_DIRECTOR_API_TOKEN` | idem |
| Relay | ✓ | ✓ |

### OBS joueur (RTMP)

| Joueur | URL |
|--------|-----|
| A | `rtmp://VPS:1935/live/playerA` |
| B | `rtmp://VPS:1935/live/playerB` |

## OBS régie

Scènes : `PLAYER_A`, `PLAYER_B`, `SPLIT`

| Mode | Commande |
|------|----------|
| Sans OBS | `OBS_ENABLED=false` (défaut) |
| Docker OBS | `OBS_ENABLED=true` + `docker compose --profile full up -d` |
| OBS hôte Linux | `OBS_ENABLED=true`, `OBS_HOST=172.17.0.1` |

### Twitch via `.env` (conteneur OBS)

Dans `.env`, avant `docker compose --profile full up -d` :

```bash
TWITCH_STREAM_KEY=live_xxxxxxxx   # clé Twitch (Dashboard → Stream)
TWITCH_SERVER=                    # vide = ingest auto Twitch
TWITCH_SERVICE=Twitch             # défaut
```

Au démarrage du conteneur `obs`, le stream Twitch démarre automatiquement si `TWITCH_STREAM_KEY` est défini (`TWITCH_AUTO_START=true` par défaut). Scènes RTMP joueurs à configurer une fois dans OBS régie.

## HTTPS

1. DNS → VPS
2. Décommenter bloc domaine dans `docker/caddy/Caddyfile`
3. `docker compose restart caddy`

## Logs

```bash
docker compose logs -f director
docker compose exec director ls /data/logs
```

## Build client Windows (hors Docker)

Sur une machine Windows :

```bat
build-client.bat
→ dist\LolCamSwitcherClient.exe
```

Variables : voir [`.env.example`](https://github.com/RajPorus19/LolCamSwitcher/blob/main/.env.example) sur GitHub.

Guide opérationnel complet (token, OBS joueur, OBS régie) : **[SETUP.md](SETUP.md)**.
