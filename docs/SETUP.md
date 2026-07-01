# Guide de setup complet — de zéro au live

Ce document répond aux questions concrètes après déploiement du serveur :

- **Où est le token API ?** Comment le donner aux joueurs ?
- **Que configure-t-on sur le serveur** vs **sur chaque PC joueur** ?
- **Quels réglages OBS** pour envoyer la vidéo vers le VPS ?
- **Comment l'OBS régie** récupère les deux POV et stream sur Twitch ?

> Architecture : clients Windows (`LoLAutoDirectorClient.exe`) + serveur Linux Docker.  
> Schémas détaillés : [CLIENT_SERVER.md](CLIENT_SERVER.md) · Docker : [DOCKER.md](DOCKER.md)

---

## Vue d'ensemble — qui configure quoi ?

| Élément | Où ça se configure | Comment le serveur le « sait » |
|---------|-------------------|----------------------------------|
| **Token API** | `.env` sur le VPS | Tu le **choisis toi-même** au déploiement |
| **Joueur A vs B** | Client `.exe` sur chaque PC | Le client envoie `"player": "A"` ou `"B"` |
| **Pseudo Riot** | Client `.exe` | Envoyé dans chaque event / heartbeat |
| **Flux vidéo joueur A** | OBS du PC A | Convention fixe : clé RTMP `playerA` |
| **Flux vidéo joueur B** | OBS du PC B | Convention fixe : clé RTMP `playerB` |
| **Scènes régie** | OBS sur le VPS | Tu crées `PLAYER_A`, `PLAYER_B`, `SPLIT` |
| **Stream Twitch final** | OBS régie | Clé Twitch dans OBS régie uniquement |

**Il n'y a pas de panneau admin** pour enregistrer les joueurs ni de token par joueur.  
Le serveur reçoit les events HTTP (slot A/B déclaré par le client) et les flux RTMP (clés `playerA` / `playerB`).

---

## Étape 0 — Prérequis

| Ressource | Détail |
|-----------|--------|
| **VPS Linux** | Ubuntu/Debian, 2+ vCPU, 4 Go RAM recommandé si OBS régie |
| **IP publique ou domaine** | Ex. `203.0.113.50` ou `regie.monstream.fr` |
| **Ports ouverts** | `1935` (RTMP), `80`/`443` (API clients), optionnel `8080` (preview HLS) |
| **2 PC Windows** | Un par joueur — LoL + client + OBS |
| **Clé stream Twitch** | Uniquement pour l'**OBS régie** (pas les joueurs) |

---

## Étape 1 — Déployer le serveur Docker

```bash
ssh user@VPS
git clone https://github.com/RajPorus19/LolCamSwitcher.git
cd LolCamSwitcher
cp .env.example .env
nano .env          # ← étape critique : token + domaine
docker compose up -d
```

Vérifier que tout tourne :

```bash
docker compose ps
curl http://localhost/health
# → {"status":"ok","obs_enabled":false,"clients":[],...}
```

---

## Étape 2 — Token API : création, récupération, partage

### Comment ça marche

Le token **n'est pas généré par une interface**. **C'est toi qui le définis** dans `.env` **avant** le premier `docker compose up`.

```bash
# .env sur le VPS
LOL_DIRECTOR_API_TOKEN=K7mP9xR2vN4wQ8sT1uY6zA3bC5dE0fG
```

| Question | Réponse |
|----------|---------|
| Où le récupérer après deploy ? | `cat .env` sur le VPS (variable `LOL_DIRECTOR_API_TOKEN`) |
| Un token par joueur ? | **Non** — un seul token partagé par tous les clients |
| Où le mettre côté joueur ? | Champ **Token API** dans `LoLAutoDirectorClient.exe` |
| Format HTTP | Header `Authorization: Bearer K7mP9xR2vN4wQ8sT1uY6zA3bC5dE0fG` |
| Token perdu ? | Regénère une nouvelle valeur dans `.env` puis `docker compose up -d` — mets à jour tous les clients |

### Générer un token sécurisé

```bash
# Linux / macOS
openssl rand -hex 32

# ou Python
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copie le résultat dans `.env` :

```bash
LOL_DIRECTOR_API_TOKEN=<valeur générée>
REQUIRE_API_TOKEN=true
```

Redémarre le director si tu changes le token :

```bash
docker compose up -d director
```

### Tester le token

```bash
export TOKEN="K7mP9xR2vN4wQ8sT1uY6zA3bC5dE0fG"
export VPS="http://203.0.113.50"    # ou https://regie.monstream.fr

curl "$VPS/health"                                    # public, sans token
curl -H "Authorization: Bearer $TOKEN" "$VPS/api/v1/status"
# → 200 OK avec game_time, focus, clients_connected, etc.

# Sans token ou mauvais token → 401/403
```

### Fiche à envoyer aux joueurs (events)

```
URL serveur :  http://203.0.113.50
               (ou https://regie.monstream.fr si HTTPS activé)

Token API :    K7mP9xR2vN4wQ8sT1uY6zA3bC5dE0fG

⚠ Ne partage pas ce token publiquement (Discord public, stream overlay, etc.)
```

---

## Étape 3 — Fichier `.env` serveur (référence)

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `LOL_DIRECTOR_API_TOKEN` | **Oui** | Secret partagé avec les clients Windows |
| `REQUIRE_API_TOKEN` | Oui (prod) | `true` — refuse le démarrage sans token |
| `OBS_ENABLED` | Non | `false` = API seule ; `true` = director pilote OBS régie |
| `OBS_HOST` | Si OBS | `obs` (container Docker) ou `172.17.0.1` (OBS sur l'hôte Linux) |
| `OBS_PORT` | Si OBS | `4455` (WebSocket v5) |
| `OBS_PASSWORD` | Si OBS | Mot de passe WebSocket OBS régie |
| `AUTO_MODE` | Non | `true` = switch caméra auto sur events |
| `DOMAIN` | Recommandé | Domaine pour HTTPS Caddy |
| `RTMP_PORT` | Non | Défaut `1935` |
| `HTTP_PORT` / `HTTPS_PORT` | Non | Défaut `80` / `443` |

Exemple production minimal (sans OBS régie, pour tester events + RTMP ingest) :

```bash
LOL_DIRECTOR_API_TOKEN=K7mP9xR2vN4wQ8sT1uY6zA3bC5dE0fG
REQUIRE_API_TOKEN=true
OBS_ENABLED=false
AUTO_MODE=true
DOMAIN=regie.monstream.fr
```

---

## Étape 4 — Fiches joueur (copier-coller)

Remplace `203.0.113.50` par ton IP ou domaine, et `TOKEN` par ta valeur `.env`.

### Joueur A

| Composant | Réglage |
|-----------|---------|
| **LoLAutoDirectorClient.exe** | |
| Slot | `Joueur A` |
| Pseudo Riot | Nom **exact** in-game (voir `https://127.0.0.1:2999/liveclientdata/playerlist`) |
| Relayer vers le serveur | ✓ coché |
| URL serveur | `http://203.0.113.50` ou `https://regie.monstream.fr` |
| Token API | `TOKEN` |
| **OBS (stream vers VPS)** | |
| Service | **Custom…** |
| Serveur | `rtmp://203.0.113.50:1935/live` |
| Clé de stream | `playerA` |
| URL complète | `rtmp://203.0.113.50:1935/live/playerA` |

### Joueur B

Identique, sauf :

| Composant | Réglage |
|-----------|---------|
| Slot | `Joueur B` |
| Clé de stream OBS | `playerB` |
| URL complète RTMP | `rtmp://203.0.113.50:1935/live/playerB` |

> **Important** : le slot A/B dans le client `.exe` doit correspondre à la clé RTMP (`playerA` ↔ slot A).  
> Si le joueur B envoie sa vidéo avec la clé `playerA`, la régie affichera le mauvais POV.

---

## Étape 5 — OBS joueur : envoyer sa caméra au VPS

Chaque joueur stream **vers ton serveur**, pas vers Twitch directement.

### Configuration OBS (Windows)

1. **Paramètres** → **Stream**
2. Service : **Custom…**
3. Serveur : `rtmp://IP_OU_DOMAINE_VPS:1935/live`
4. Clé de stream :
   - Joueur A → `playerA`
   - Joueur B → `playerB`
5. **Paramètres** → **Sortie** → bitrate adapté (ex. 2500–6000 Kbps, x264/NVENC)
6. **Démarrer le stream** dans OBS **avant** ou **pendant** la partie

### Vérifier que le flux arrive sur le VPS

**Option A — Preview HLS** (port 8080 ouvert sur le firewall) :

```
http://203.0.113.50:8080/hls/playerA.m3u8
http://203.0.113.50:8080/hls/playerB.m3u8
```

Ouvre dans VLC ou un navigateur compatible HLS.

**Option B — Stats RTMP** :

```
http://203.0.113.50:8080/stat
```

Tu dois voir un publish actif sur `live/playerA` ou `live/playerB`.

**Option C — Logs nginx** :

```bash
docker compose logs rtmp
```

### Dépannage RTMP joueur

| Symptôme | Cause probable | Fix |
|----------|----------------|-----|
| OBS « Failed to connect » | Port 1935 fermé | Ouvrir `1935/tcp` sur le firewall VPS + provider cloud |
| Flux OK mais mauvais POV en régie | Clé stream inversée | A → `playerA`, B → `playerB` |
| Latence élevée | Bitrate / encodeur | Réduire résolution, NVENC, keyframe 2s |

---

## Étape 6 — Client Windows : events vers le serveur

1. Télécharger **`LoLAutoDirectorClient.exe`** ([Releases](https://github.com/RajPorus19/LolCamSwitcher/releases))
2. Remplir la fiche joueur (étape 4)
3. Cliquer **Tester connexion serveur** → barre de statut `Serveur OK — token valide`
4. Lancer une partie LoL (Practice Tool OK)
5. Cliquer **Démarrer**
6. Vérifier :
   - `LoL : ✓ connecté`
   - `Serveur : ✓ connecté`

Côté VPS :

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/status | jq
# clients_connected: ["A"] ou ["A","B"]
```

Ou :

```bash
curl http://localhost/health | jq
# "clients": ["A", "B"]
```

> L'URL serveur passe par **Caddy** (port 80/443), **pas** `:8750`.  
> `:8750` est interne au réseau Docker.

---

## Étape 7 — OBS régie (VPS) : recevoir les POV + stream Twitch

L'OBS régie est le **seul** OBS qui stream vers Twitch/YouTube.

### Scènes obligatoires

Crée exactement ces noms (le director les cible) :

| Scène | Contenu |
|-------|---------|
| `PLAYER_A` | Source vidéo du flux joueur A |
| `PLAYER_B` | Source vidéo du flux joueur B |
| `SPLIT` | Les deux POV côte à côte (layout libre) |

### Sources vidéo (depuis nginx-rtmp)

Dans OBS régie, ajoute des sources **Media Source** ou **VLC Video Source** :

| Source | URL (réseau Docker) | URL (OBS sur hôte Linux) |
|--------|---------------------|--------------------------|
| POV A | `rtmp://rtmp:1935/live/playerA` | `rtmp://127.0.0.1:1935/live/playerA` |
| POV B | `rtmp://rtmp:1935/live/playerB` | `rtmp://127.0.0.1:1935/live/playerB` |

> `rtmp` est le nom du service Docker `lol-rtmp` sur le réseau `regie`.

Alternative en **HTTP/HLS** (plus simple à tester, plus de latence) :

```
http://203.0.113.50:8080/hls/playerA.m3u8
http://203.0.113.50:8080/hls/playerB.m3u8
```

### WebSocket OBS (pilotage auto)

**Paramètres OBS** → **WebSocket** :

| Réglage | Valeur |
|---------|--------|
| Activer | ✓ |
| Port | `4455` |
| Mot de passe | Identique à `OBS_PASSWORD` dans `.env` |

Dans `.env` :

```bash
OBS_ENABLED=true
OBS_HOST=obs          # container Docker profile full
OBS_PORT=4455
OBS_PASSWORD=mon-mot-de-passe-obs
AUTO_MODE=true
```

Puis :

```bash
docker compose --profile full up -d
```

### Stream Twitch (OBS régie uniquement)

**Paramètres** → **Stream** → Service **Twitch** → connecte ton compte ou colle la clé stream.

Les joueurs **ne streament pas** sur Twitch — ils poussent uniquement vers ton VPS en RTMP.

---

## Étape 8 — HTTPS (recommandé pour les clients)

1. DNS : `regie.monstream.fr` → IP du VPS
2. Dans `.env` : `DOMAIN=regie.monstream.fr`
3. Décommenter le bloc domaine dans `docker/caddy/Caddyfile` :

```
{$DOMAIN} {
    encode gzip
    reverse_proxy director:8750
}
```

4. `docker compose restart caddy`
5. Clients : URL = `https://regie.monstream.fr` (sans port)

Caddy obtient automatiquement un certificat Let's Encrypt.

---

## Étape 9 — Checklist avant le live

### Serveur

- [ ] `docker compose ps` — tous les services `Up`
- [ ] `curl http://VPS/health` → `"status":"ok"`
- [ ] Token défini dans `.env` et testé avec `/api/v1/status`
- [ ] Port **1935** ouvert (RTMP joueurs)
- [ ] Port **80/443** ouvert (API clients)

### Joueur A

- [ ] Client : slot **A**, pseudo exact, relay ON, token OK
- [ ] Client : **Tester connexion serveur** → OK
- [ ] OBS : stream vers `rtmp://VPS:1935/live` clé **`playerA`**
- [ ] Preview HLS `playerA.m3u8` visible (optionnel)
- [ ] LoL lancé, client **Démarrer**, `LoL ✓` + `Serveur ✓`

### Joueur B

- [ ] Idem avec slot **B** et clé **`playerB`**

### Régie

- [ ] Scènes `PLAYER_A`, `PLAYER_B`, `SPLIT` créées
- [ ] Sources RTMP/HLS affichent les deux POV
- [ ] OBS WebSocket activé, `OBS_ENABLED=true`, director connecté
- [ ] `curl /api/v1/status` → `obs_connected: true`, `clients_connected: ["A","B"]`
- [ ] Stream Twitch test depuis OBS régie

---

## Ordre de démarrage recommandé

```
1. VPS       docker compose up -d
2. Régie     OBS régie ouvert, sources POV actives, WebSocket ON
3. Joueur A  OBS stream ON → client .exe Démarrer → LoL
4. Joueur B  idem
5. Régie     Démarrer stream Twitch
6. Vérifier  /api/v1/status + switch auto sur un kill test
```

---

## FAQ

### Le serveur sait-il quel summoner est A ou B ?

Oui, **via le client** : chaque heartbeat/event inclut `"player": "A"` ou `"B"` + le pseudo Riot.  
Rien à renseigner manuellement côté serveur.

### Peut-on avoir un token différent par joueur ?

**Non** (v1.4). Un token partagé. Pour révoquer l'accès d'un joueur, change le token et redistribue-le aux autres.

### Les joueurs ont-ils besoin de la clé Twitch ?

**Non.** Seule l'OBS régie stream vers Twitch.

### Le client gère-t-il la vidéo ?

**Non.** Vidéo = OBS joueur → RTMP. Events = client `.exe` → HTTPS.

### URL serveur : avec ou sans `/api` ?

**Sans.** Ex. `http://203.0.113.50` — le client ajoute `/api/v1/events` automatiquement.

### Comment voir les logs d'une partie ?

```bash
docker compose exec director ls /data/logs
docker compose exec director tail -f /data/logs/game_XXXX.log
```

---

## Voir aussi

| Document | Contenu |
|----------|---------|
| [TESTING.md](TESTING.md) | Tester la détection events **sans** serveur ni stream |
| [CLIENT_SERVER.md](CLIENT_SERVER.md) | Schémas, API, comparaison des modes |
| [DOCKER.md](DOCKER.md) | Détails Docker, ports, profiles |
| [README.md](index.md) | Vue d'ensemble du projet |
