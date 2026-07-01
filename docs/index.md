# LoL Auto Director

Régie automatique pour broadcast **League of Legends dual-POV** (joueur A + joueur B).

Le système détecte les events live (kills, objectifs, combats…) et commande l'**OBS central** sur le VPS pour basculer entre `PLAYER_A`, `PLAYER_B` et `SPLIT`.

!!! tip "Par où commencer ?"
    Suis le **[Guide de setup](SETUP.md)** — étape par étape, de zéro au live Twitch.

---

## Architecture

```
PC Joueur A (Windows)          PC Joueur B (Windows)
  LoL + Client .exe              LoL + Client .exe
  OBS → RTMP playerA             OBS → RTMP playerB
         │                              │
         └──────────┬───────────────────┘
                    ▼
         VPS Linux (docker compose)
           Caddy → director → OBS régie → Twitch
           nginx-rtmp (ingest vidéo)
```

| Composant | OS | Rôle |
|-----------|-----|------|
| **LoLAutoDirectorClient.exe** | Windows | Events LoL + relay vers le VPS |
| **OBS joueur** | Windows | Capture POV → RTMP vers le VPS |
| **director + nginx-rtmp + Caddy** | Linux (Docker) | API, ingest vidéo, régie |
| **OBS régie** | Linux | Switch caméra + stream Twitch |

---

## Démarrage rapide

### 1. Serveur (VPS Linux)

```bash
git clone https://github.com/RajPorus19/LolCamSwitcher.git
cd LolCamSwitcher
cp .env.example .env    # définir LOL_DIRECTOR_API_TOKEN
docker compose up -d
```

### 2. Clients (Windows)

Télécharge **[LoLAutoDirectorClient.exe](https://github.com/RajPorus19/LolCamSwitcher/releases)** et configure slot A/B + token.

### 3. OBS joueurs

| Joueur | Serveur RTMP | Clé stream |
|--------|--------------|------------|
| A | `rtmp://VPS:1935/live` | `playerA` |
| B | `rtmp://VPS:1935/live` | `playerB` |

→ Détail complet : **[Guide de setup](SETUP.md)**

---

## Documentation

| Guide | Description |
|-------|-------------|
| **[Setup pas-à-pas](SETUP.md)** | Token, OBS joueur, OBS régie, checklist live |
| [Architecture](CLIENT_SERVER.md) | Schémas, API, modes d'utilisation |
| [Docker](DOCKER.md) | Compose, ports, HTTPS |
| [Tests](TESTING.md) | Valider la détection events sans stream |
| [Changelog](CHANGELOG.md) | Historique des versions |

---

## Sécurité

- Compatible **Vanguard** — API Riot Live Client locale, aucune injection mémoire
- API serveur protégée par **Bearer token**

[Télécharger les releases →](https://github.com/RajPorus19/LolCamSwitcher/releases)
