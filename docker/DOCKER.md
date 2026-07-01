# Déploiement Docker — serveur Linux (VPS)

Stack de production pour la **régie centrale**. Les **clients Windows** (`.exe`) tournent sur les PC joueurs.

## Architecture

```
                    Internet
                       │
         ┌─────────────┼─────────────┐
         │             │             │
    RTMP :1935    HTTPS :80/443   (Twitch via OBS)
         │             │
    ┌────▼────┐   ┌────▼────┐
    │  rtmp   │   │  caddy  │──► director:8750 (API)
    │ nginx   │   └─────────┘
    └────┬────┘
         │ rtmp://rtmp:1935/live/playerA|B
    ┌────▼────┐  (profile full)
    │   obs   │──► stream Twitch
    └─────────┘
```

| Service | Rôle |
|---------|------|
| **director** | API events + régie (Python) |
| **rtmp** | Ingest 2 flux OBS joueurs |
| **caddy** | Reverse proxy HTTP(S) vers l'API |
| **obs** | Optionnel (`--profile full`) — switch caméra + sortie Twitch |

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

## Ports à ouvrir (firewall VPS)

| Port | Service | Public |
|------|---------|--------|
| 1935/tcp | RTMP ingest joueurs | Oui |
| 80, 443 | API clients (Caddy) | Oui |
| 8750 | Director direct | Non (interne) |
| 4455 | OBS WebSocket | Non |
| 8080 | HLS preview | Optionnel |

## Configuration joueurs

### Events (client Windows `.exe`)

- URL serveur : `http://IP_VPS` ou `https://regie.tondomaine.com`
- Token : valeur de `LOL_DIRECTOR_API_TOKEN` dans `.env`
- Slot A sur PC joueur A, slot B sur PC joueur B

### Vidéo (OBS joueur → RTMP)

| Joueur | URL RTMP |
|--------|----------|
| A | `rtmp://IP_VPS:1935/live/playerA` |
| B | `rtmp://IP_VPS:1935/live/playerB` |

Clé stream : laisser vide (ou `playerA` / `playerB` selon config OBS).

## OBS régie (3 options)

### Option 1 — Sans OBS (défaut)

`OBS_ENABLED=false` dans `.env` — API + logs + scores, pas de switch caméra Twitch.

### Option 2 — OBS headless Docker (expérimental)

```bash
# .env : OBS_ENABLED=true
docker compose --profile full up -d
```

Configurer manuellement dans OBS (via VNC si besoin) les scènes :
- `PLAYER_A` → source Media `rtmp://rtmp:1935/live/playerA`
- `PLAYER_B` → source Media `rtmp://rtmp:1935/live/playerB`
- `SPLIT` → layout 50/50

WebSocket OBS : port 4455, mot de passe = `OBS_PASSWORD` dans `.env`.

### Option 3 — OBS sur l'hôte Linux (recommandé prod)

Installer OBS sur le VPS, configurer les scènes, puis :

```env
OBS_ENABLED=true
OBS_HOST=host.docker.internal   # Docker Desktop
# ou IP de l'hôte sur le bridge docker, ex. 172.17.0.1
```

Ne pas lancer le service `obs` du compose.

## HTTPS avec domaine

1. Pointer `regie.example.com` vers le VPS
2. Dans `.env` : `DOMAIN=regie.example.com`
3. Décommenter le bloc HTTPS dans `docker/caddy/Caddyfile`
4. `docker compose up -d caddy`

Clients : `https://regie.example.com`

## Logs régie

Volume Docker `director-logs` → `/data/logs/game_*.log` dans le conteneur.

```bash
docker compose exec director ls -la /data/logs
```

## Commandes utiles

```bash
docker compose logs -f director
docker compose ps
docker compose down
docker compose build --no-cache director
docker compose --profile full up -d   # avec OBS
```

## Build client Windows (.exe)

Sur une machine Windows :

```bat
build-client.bat
```

Produit : `dist\LoLAutoDirectorClient.exe`

Le serveur Docker **ne nécessite pas** PySide6 ni PyInstaller.

## Variables d'environnement (.env)

Voir [.env.example](../.env.example).
