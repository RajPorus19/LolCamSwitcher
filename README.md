# LoL Auto Director

Régie automatique pour broadcast **League of Legends dual-POV** (joueur A + joueur B).

Le système détecte les events live (kills, objectifs, combats…) et commande l'**OBS central** sur le VPS pour basculer entre `PLAYER_A`, `PLAYER_B` et `SPLIT`.

> **Deux binaires distincts** : client Windows sur les PC joueurs · serveur Linux (Docker) sur le VPS.

---

## Architecture (production)

```
┌──────────────────────────────┐       ┌──────────────────────────────┐
│   PC JOUEUR A  (Windows)     │       │   PC JOUEUR B  (Windows)     │
│                              │       │                              │
│  LoL                         │       │  LoL                         │
│  LoLAutoDirectorClient.exe   │       │  LoLAutoDirectorClient.exe   │
│    └─ events locaux (LoL API)│       │    └─ events locaux          │
│    └─ relay HTTPS ───────────┼───┐   │    └─ relay HTTPS ───────────┼───┐
│                              │   │   │                              │   │
│  OBS → RTMP :1935/playerA ───┼───┼───┼── OBS → RTMP :1935/playerB ──┼───┤
└──────────────────────────────┘   │   └──────────────────────────────┘   │
                                   │                                      │
                                   ▼                                      ▼
              ┌────────────────────────────────────────────────────────────┐
              │              VPS Linux — docker compose up -d               │
              │                                                            │
              │   ┌─────────┐    ┌───────────┐    ┌─────────────────────┐  │
              │   │  Caddy  │───►│ director  │───►│ OBS (profile full   │  │
              │   │ :80/443 │    │ API régie │    │  ou hôte Linux)     │  │
              │   └────▲────┘    └───────────┘    │  PLAYER_A / B / SPLIT│  │
              │        │ Bearer token               └──────────┬──────────┘  │
              │   clients events                              │ stream       │
              │   ┌─────────┐    ┌───────────────────────────┘              │
              │   │ nginx   │◄───┘ rtmp://rtmp:1935/live/playerA|B         │
              │   │ RTMP    │                                               │
              │   │ :1935   │                                               │
              │   └─────────┘                                               │
              └───────────────────────────────┬──────────────────────────────┘
                                              ▼
                                       Twitch / YouTube
```

### Qui fait quoi ?

| Composant | OS | Rôle |
|-----------|-----|------|
| **LoLAutoDirectorClient.exe** | Windows | Lit l'API LoL locale · affiche events · relay vers VPS |
| **OBS joueur** | Windows | Capture POV → push RTMP vers le VPS |
| **director** (Docker) | Linux | API + régie (scores, stratégies, logs) |
| **nginx-rtmp** (Docker) | Linux | Ingest 2 flux vidéo |
| **Caddy** (Docker) | Linux | HTTPS + proxy API clients |
| **OBS régie** | Linux | Mix + switch caméra + stream Twitch |

L'OBS des joueurs **n'est pas piloté** par le programme — seul l'OBS **central** sur le VPS l'est.

---

## Démarrage rapide

### 1. Serveur VPS (Linux)

```bash
git clone https://github.com/RajPorus19/LolCamSwitcher.git
cd LolCamSwitcher
cp .env.example .env          # définir LOL_DIRECTOR_API_TOKEN
docker compose up -d
```

→ Guide complet : **[docs/DOCKER.md](docs/DOCKER.md)**

### 2. Clients joueurs (Windows)

→ Fiches détaillées joueur A/B, token, OBS : **[docs/SETUP.md](docs/SETUP.md)** (étapes 4–6)

Télécharger **`LoLAutoDirectorClient.exe`** depuis [Releases](https://github.com/RajPorus19/LolCamSwitcher/releases) ou :

```bat
build-client.bat
```

| Champ client | Joueur A | Joueur B |
|--------------|----------|----------|
| Slot | A | B |
| URL serveur | `http://IP_VPS` | idem |
| Token | `LOL_DIRECTOR_API_TOKEN` | idem |
| Relay | ✓ | ✓ |

### 3. RTMP (OBS joueur)

| Joueur | URL stream |
|--------|------------|
| A | `rtmp://IP_VPS:1935/live/playerA` |
| B | `rtmp://IP_VPS:1935/live/playerB` |

---

## Modes d'utilisation

| Mode | Commande | Usage |
|------|----------|-------|
| **Client agent** | `LoLAutoDirectorClient.exe` | PC joueur — events + relay |
| **Serveur Docker** | `docker compose up -d` | VPS Linux — régie + RTMP |
| **Director GUI** (legacy) | `LoLAutoDirector.exe` / `main.py` | Tout-en-un local Windows |

| Mode client | Serveur | Stream Twitch |
|-------------|---------|---------------|
| Client standalone | ✗ | ✗ (events only) |
| Client + serveur Docker | ✓ | ✓ |
| Director GUI local | local | ✓ (1 machine) |

---

## Stratégies de switch

| Stratégie | Comportement |
|-----------|--------------|
| **Score** | Priorité kills/objectifs + split si 2 gros plays proches |
| **Joueur principal** | Focus A (ou B), bascule temporaire sur l'autre |
| **Dual** | Alternance : reste sur le joueur actif jusqu'à l'action de l'autre |

**Replay instantané** : délai configurable (défaut −3 s) — kill à 20:00 → focus dès 19:57.

---

## Documentation

Toute la doc détaillée est dans **[docs/](docs/)** :

| Document | Contenu |
|----------|---------|
| **[docs/SETUP.md](docs/SETUP.md)** | **Guide complet** — token, OBS joueur, OBS régie, fiches A/B |
| [docs/CLIENT_SERVER.md](docs/CLIENT_SERVER.md) | Schémas, API, comparaison des modes |
| [docs/DOCKER.md](docs/DOCKER.md) | Compose, ports, OBS régie, HTTPS |
| [docs/TESTING.md](docs/TESTING.md) | Tester events sans stream |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Versions |

---

## Tests (sans stream)

Practice Tool + client ou script sonde — voir **[docs/TESTING.md](docs/TESTING.md)**.

```bat
python scripts/test_live_events.py --player-a "TonPseudo" --watch
```

---

## Builds Windows

| Script | Produit | Cible |
|--------|---------|-------|
| `build-client.bat` | `LoLAutoDirectorClient.exe` | **PC joueurs** |
| `build.bat` | `LoLAutoDirector.exe` | Director GUI local (legacy) |

Le **serveur** tourne sous **Docker/Linux** — pas de `.exe` serveur.

---

## Structure du projet

```
lol_auto_director/
├── client/          # agent Windows (events + relay)
├── server/          # API FastAPI (Linux)
├── director/        # scoring, stratégies, timeline
├── lol/             # Riot Live Client API
├── obs/             # OBS WebSocket v5
└── session_log/     # logs par partie

docker/
├── director/        # Dockerfile serveur
├── nginx-rtmp/      # ingest RTMP
├── caddy/           # reverse proxy
└── obs/             # OBS headless (optionnel)

docker-compose.yml
client_main.py       # entry client
server_main.py       # entry serveur
main.py              # entry legacy GUI
```

---

## Sécurité / Vanguard

- Aucune injection, aucune lecture mémoire
- API Riot **Live Client** locale (port 2999) sur chaque PC joueur
- API serveur protégée par **Bearer token**
- Compatible Vanguard

---

## Releases

**https://github.com/RajPorus19/LolCamSwitcher/releases**

Version actuelle : **1.4.0** — voir [docs/CHANGELOG.md](docs/CHANGELOG.md).

Assets : `LoLAutoDirectorClient.exe` (joueurs) · `LoLAutoDirector.exe` (legacy).
