# Client / Serveur — guide setup

## Vue d'ensemble

```
PC Joueur A                         PC Joueur B
  LoL + client_main.py                LoL + client_main.py
       │  HTTPS events + heartbeat         │
       └────────────┬──────────────────────┘
                    ▼
           VPS — server_main.py
             ├─ API (Bearer token)
             ├─ Director + OBS central
             ├─ 2 flux RTMP (OBS joueurs)
             └─ → Twitch
```

- **Vidéo** : OBS de chaque joueur → RTMP vers le VPS (inchangé)
- **Events** : client agent → API HTTP du serveur (nouveau)

---

## 1. Serveur (VPS / régie)

### Lancer

```bat
set LOL_DIRECTOR_API_TOKEN=mon-token-secret-long
python server_main.py --host 0.0.0.0 --port 8750
```

Sans variable d'environnement, un token aléatoire est généré et affiché **une fois** au démarrage — copiez-le pour les clients.

### Prérequis serveur

- Windows (OBS + LoL Auto Director)
- OBS Studio avec WebSocket v5 (port 4455)
- Scènes `PLAYER_A`, `PLAYER_B`, `SPLIT`
- RTMP ingest pour les 2 flux joueurs
- Port **8750** ouvert (API clients)

### API

| Route | Auth | Body |
|-------|------|------|
| `GET /health` | Non | — |
| `GET /api/v1/status` | Bearer | — |
| `POST /api/v1/events` | Bearer | `{ "player": "A", "type": "kill", "time": 120.5 }` |
| `POST /api/v1/heartbeat` | Bearer | `{ "player": "A", "game_time": 120.5, "lol_connected": true }` |

Header obligatoire (sauf `/health`) :

```
Authorization: Bearer mon-token-secret-long
```

---

## 2. Client (PC joueur)

### Standalone — sans serveur

```bat
python client_main.py
```

- Entrer **Slot** (A ou B) et **Pseudo Riot**
- **Démarrer** — les events s'affichent en live
- Pas besoin d'URL serveur ni de token

### Relay — vers le serveur

1. Cocher **Relayer les events vers le serveur**
2. URL : `http://IP_DU_VPS:8750`
3. Token : le même que `LOL_DIRECTOR_API_TOKEN`
4. **Tester connexion serveur** → doit afficher OK
5. **Démarrer**

Chaque event détecté localement est envoyé au serveur qui fait la régie OBS.

---

## 3. Checklist live

- [ ] Serveur lancé, token noté
- [ ] OBS régie connecté (WebSocket)
- [ ] 2 flux RTMP visibles dans OBS régie
- [ ] Client A : slot A, relay ON, LoL ✓
- [ ] Client B : slot B, relay ON, LoL ✓
- [ ] `GET /api/v1/status` montre `clients_connected: ["A", "B"]`

### Test rapide status (curl)

```bash
curl -s http://VPS:8750/health
curl -s -H "Authorization: Bearer TOKEN" http://VPS:8750/api/v1/status
```

---

## 4. Sécurité

- Utilisez un token long et aléatoire
- En production, placez l'API derrière HTTPS (reverse proxy nginx/Caddy)
- N'exposez que le port nécessaire au VPS

---

## 5. Modes comparés

| | Client seul | Client + serveur | main.py (legacy) |
|--|-------------|------------------|------------------|
| Events live | ✓ | ✓ | ✓ |
| Stream Twitch | ✗ | ✓ (via OBS régie) | ✓ |
| LoL sur régie | ✗ | ✗ | Spectateur requis |
| 2 PC distants | ✓ events | ✓ complet | ✗ |
