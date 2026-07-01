# Client / Serveur

Guide setup pour l'architecture **distribuée** : clients Windows + serveur Linux Docker.

> **Guide pas-à-pas complet** (token API, OBS joueur, OBS régie, fiches joueur) : **[SETUP.md](SETUP.md)**

## Schéma complet

```
┌──────────────── PC JOUEUR A (Windows) ─────────────────┐
│  LoL  ←── Riot Live Client API (127.0.0.1:2999)        │
│  LolCamSwitcherClient.exe                             │
│    • mode standalone : events visibles en local        │
│    • mode relay : POST events + heartbeat ─────────────┼──┐
│  OBS ── RTMP ──────────────────────────────────────────┼──┼──┐
└────────────────────────────────────────────────────────┘  │  │
                                                              │  │
┌──────────────── PC JOUEUR B (Windows) ─────────────────┐  │  │
│  (identique, slot B)                                    │  │  │
└─────────────────────────────────────────────────────────┘  │  │
                                                             │  │
         ┌───────────────────────────────────────────────────┘  │
         │  HTTPS  Authorization: Bearer TOKEN                   │
         │  POST /api/v1/events  ·  POST /api/v1/heartbeat       │
         ▼                                                       │
┌──────────────── VPS Linux (docker compose) ──────────────────┼──┘
│                                                              │
│  ┌─────────┐      ┌────────────┐      ┌──────────────────┐  │
│  │  Caddy  │─────►│  director  │─────►│ OBS régie        │  │
│  │  :443   │      │  (Python)  │ WS   │ PLAYER_A/B/SPLIT │──┼──► Twitch
│  └─────────┘      └────────────┘      └────────▲─────────┘  │
│                                                 │            │
│  ┌─────────┐   rtmp://rtmp:1935/live/playerA ──┘            │
│  │ nginx   │◄── rtmp://rtmp:1935/live/playerB ◄──────────────┘
│  │ RTMP    │      (flux OBS joueurs)
│  │ :1935   │
│  └─────────┘
└──────────────────────────────────────────────────────────────
```

---

## Modèle de configuration (important)

| Quoi | Où | Notes |
|------|-----|-------|
| Token API | `.env` VPS (`LOL_DIRECTOR_API_TOKEN`) | **Tu le choisis** — pas de panneau admin |
| Joueur A / B | Client `.exe` (slot + pseudo) | Le serveur **ne** stocke pas une liste de joueurs |
| Flux RTMP A | OBS joueur A | Clé fixe `playerA` |
| Flux RTMP B | OBS joueur B | Clé fixe `playerB` |
| Scènes régie | OBS VPS | `PLAYER_A`, `PLAYER_B`, `SPLIT` |
| Twitch | OBS régie seulement | Les joueurs streament vers le VPS, pas Twitch |

→ Détail opérationnel : **[SETUP.md](SETUP.md)** (étapes 2 à 7)

---

## 1. Serveur (VPS Linux)

### Docker (recommandé)

```bash
cp .env.example .env
# Obligatoire :
#   LOL_DIRECTOR_API_TOKEN=un-secret-long-et-fixe
#   OBS_ENABLED=false   (true si OBS régie configuré)

docker compose up -d
```

Détails : **[DOCKER.md](DOCKER.md)**

### Python direct (dev)

```bash
export LOL_DIRECTOR_API_TOKEN=mon-token
export OBS_ENABLED=false
python server_main.py --require-token
```

### Ports firewall

| Port | Service | Public |
|------|---------|--------|
| 1935 | RTMP (OBS joueurs) | Oui |
| 80 / 443 | API clients (Caddy) | Oui |
| 8750 | Director (interne) | Non |
| 4455 | OBS WebSocket | Non |

---

## 2. API serveur

Toutes les routes `/api/v1/*` exigent :

```
Authorization: Bearer <LOL_DIRECTOR_API_TOKEN>
```

| Route | Description |
|-------|-------------|
| `GET /health` | Public — sanity check |
| `GET /api/v1/status` | Focus, scores, clients connectés |
| `POST /api/v1/events` | `{ "player":"A", "type":"kill", "time":120.5 }` |
| `POST /api/v1/heartbeat` | `{ "player":"A", "game_time":120.5, "lol_connected":true }` |

### Test

```bash
curl http://VPS/health
curl -H "Authorization: Bearer TOKEN" http://VPS/api/v1/status
```

---

## 3. Client Windows

### Standalone (sans serveur, sans stream)

```
LolCamSwitcherClient.exe
  → Slot A ou B + pseudo Riot
  → Démarrer
  → events live dans la fenêtre (LoL ✓)
```

Aucun serveur requis. Idéal pour tester la détection events.

### Relay (production)

| Champ | Exemple |
|-------|---------|
| Slot | `A` sur PC joueur A |
| Pseudo Riot | nom exact in-game |
| URL serveur | `https://regie.example.com` ou `http://IP_VPS` |
| Token | même valeur que `.env` serveur |
| Relayer | ✓ coché |

**Tester connexion serveur** → OK → **Démarrer**

---

## 4. Vidéo RTMP (OBS joueur)

Le client **ne gère pas** la vidéo. Chaque joueur configure OBS :

| Joueur | Serveur RTMP | Clé stream |
|--------|--------------|------------|
| A | `rtmp://IP_VPS:1935/live` | `playerA` |
| B | `rtmp://IP_VPS:1935/live` | `playerB` |

Sur l'OBS régie (VPS), sources Media :
- `rtmp://rtmp:1935/live/playerA`
- `rtmp://rtmp:1935/live/playerB`

---

## 5. OBS régie (VPS)

3 scènes obligatoires : `PLAYER_A`, `PLAYER_B`, `SPLIT`

| Option | Description |
|--------|-------------|
| **Sans OBS** | `OBS_ENABLED=false` — API + scores, pas de switch caméra |
| **Docker profile full** | `docker compose --profile full up -d` |
| **OBS sur hôte Linux** | `OBS_ENABLED=true`, `OBS_HOST=172.17.0.1` |

WebSocket OBS v5 — port 4455, mot de passe = `OBS_PASSWORD` dans `.env`.

---

## 6. Checklist live

- [ ] `docker compose up -d` — services healthy
- [ ] Token fixe dans `.env` + clients configurés
- [ ] Client A : slot A, relay ON, LoL ✓
- [ ] Client B : slot B, relay ON, LoL ✓
- [ ] RTMP A et B visibles (HLS preview `:8080/hls/` optionnel)
- [ ] OBS régie : 3 scènes + stream Twitch
- [ ] `curl /api/v1/status` → `clients_connected: ["A","B"]`

---

## 7. Comparaison des modes

| | Client seul | Client + Docker | Legacy GUI |
|--|-------------|-----------------|------------|
| OS joueur | Windows | Windows | Windows |
| OS serveur | — | Linux VPS | Windows local |
| Events live | ✓ | ✓ | ✓ |
| 2 joueurs distants | ✓ | ✓ | ✗ |
| Stream Twitch | ✗ | ✓ | ✓ |
| LoL spectateur sur régie | ✗ | ✗ | requis |

Legacy = `LolCamSwitcher.exe` / `main.py` (tout sur une machine).
