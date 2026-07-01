# LoL Auto Director

Système de régie automatique pour un broadcast League of Legends à **deux POV** (joueur A + joueur B).

Le programme analyse les événements de la partie (kills, objectifs, combats…) et **commande une seule instance OBS** sur la **machine régie** pour basculer entre les scènes `PLAYER_A`, `PLAYER_B` et `SPLIT`.

> **Important** : LoL Auto Director ne pilote **pas** l’OBS de chaque joueur chez lui. Il pilote l’OBS **central** qui reçoit les deux flux vidéo et envoie le stream final vers Twitch / YouTube.

---

## Architecture réseau (2 joueurs distants)

```
┌─────────────────────┐          ┌─────────────────────┐
│   CHEZ JOUEUR A     │          │   CHEZ JOUEUR B     │
│                     │          │                     │
│  LoL (client)       │          │  LoL (client)       │
│  OBS (capture POV)  │          │  OBS (capture POV)  │
│       │             │          │       │             │
│       │ RTMP / SRT  │          │       │ RTMP / SRT  │
└───────┼─────────────┘          └───────┼─────────────┘
        │                                │
        └────────────┬───────────────────┘
                     ▼
        ┌────────────────────────────┐
        │     MACHINE RÉGIE          │
        │  (organisateur / streamer) │
        │                            │
        │  Serveur RTMP (optionnel)  │
        │       ou                   │
        │  sources Web (VDO.ninja…)  │
        │                            │
        │  OBS CENTRAL               │
        │   ├─ scène PLAYER_A        │◄── LoL Auto Director
        │   ├─ scène PLAYER_B        │    (WebSocket v5)
        │   └─ scène SPLIT           │
        │                            │
        │  LoL Auto Director (GUI)   │
        │  Client LoL (spectateur)   │◄── événements API
        │                            │
        │       │ stream final       │
        └───────┼────────────────────┘
                ▼
         Twitch / YouTube
```

### Qui stream vers où ?

| Machine | Rôle | Stream vers |
|---------|------|-------------|
| **Joueur A** | Envoie son POV | → **Machine régie** (pas Twitch directement, sauf si vous voulez un double stream) |
| **Joueur B** | Envoie son POV | → **Machine régie** |
| **Machine régie** | Mixage + régie auto | → **Twitch / YouTube** (stream public) |

Les joueurs **n’envoient pas** leur flux directement sur la chaîne finale (sauf choix volontaire de double diffusion). L’OBS central sur la machine régie est la **seule sortie publique**.

---

## Prérequis

- **Windows** sur la machine régie (le .exe est prévu pour Windows)
- **Python 3.10+** si lancement en source (`pip install -r requirements.txt`)
- **OBS Studio** sur la machine régie (WebSocket v5 activé)
- **League of Legends** sur la machine régie en mode **spectateur** de la même partie *(voir section API ci-dessous)*
- Un moyen d’**ingérer les 2 flux vidéo** des joueurs dans l’OBS central

---

## Limitation actuelle : API événements LoL

LoL Auto Director lit aujourd’hui la **Live Client Data API** de Riot :

```
https://127.0.0.1:2999
```

Cette API n’est accessible que sur **le PC où tourne un client LoL connecté à la partie**. Elle ne peut pas lire directement le client LoL d’un joueur distant.

### Conséquence pour 2 joueurs sur 2 réseaux

| Situation | Fonctionne ? |
|-----------|--------------|
| Les 2 joueurs + régie sur le même PC | Oui (peu réaliste) |
| Régie + **client LoL spectateur** de la même game | **Oui — setup recommandé** |
| Régie sans client LoL, joueurs distants seulement | **Non** (événements indisponibles) |

**Setup recommandé** : sur la **machine régie**, lancer LoL et **spectate la partie** (ou être dans la même custom game avec le client ouvert). L’API locale remonte alors tous les événements (kills, dragons, etc.) avec les noms des invocateurs. Vous renseignez ces noms dans l’interface pour identifier A et B.

> Une future version pourra ajouter un **agent léger** sur chaque PC joueur qui relaie les événements vers la régie. Ce n’est pas encore implémenté.

---

## Guide de setup complet

### Étape 1 — Flux vidéo des joueurs vers la régie

Chaque joueur configure **son OBS local** uniquement pour **envoyer** son POV à la régie. L’OBS du joueur n’est **pas** contrôlé par LoL Auto Director.

#### Option A — RTMP vers un serveur sur la machine régie (classique)

1. Sur la machine régie, installer un serveur RTMP :
   - [MediaMTX](https://github.com/bluenviron/mediamtx) (simple, gratuit)
   - ou nginx-rtmp, ou Owncast en mode ingest

2. Exposer les URLs d’ingest :
   ```
   Joueur A → rtmp://IP_REGIE:1935/live/joueurA
   Joueur B → rtmp://IP_REGIE:1935/live/joueurB
   ```

3. Ouvrir les ports sur la box de la régie (1935 TCP, ou tunnel VPN si pas d’IP publique).

4. Chaque joueur dans OBS → **Paramètres → Stream** :
   - Service : Custom
   - Serveur : l’URL RTMP ci-dessus
   - Clé : (selon config serveur)

#### Option B — VDO.ninja / OBS Ninja (sans serveur RTMP)

Pratique quand les joueurs n’ont pas d’IP fixe ou derrière NAT strict.

1. Joueur A génère un lien push sur [vdo.ninja](https://vdo.ninja/) et OBS le capture (Browser Source ou outil dédié).
2. Joueur B fait pareil.
3. Sur l’OBS régie, ajouter deux **Browser Source** (ou Media Source) avec les liens **view** de chaque joueur.

#### Option C — SRT / NDI (réseau local ou VPN)

Si les joueurs sont sur un **VPN commun** (Tailscale, ZeroTier, Hamachi…) :
- SRT caller → listener sur la régie
- ou NDI si même LAN virtuel

#### IP publique / NAT

Si la régie n’a pas d’IP publique :
- Utiliser **Tailscale** ou **ZeroTier** : les joueurs streament vers l’IP virtuelle du nœud régie.
- Ou VDO.ninja (Option B) qui traverse le NAT via WebRTC.

---

### Étape 2 — OBS central sur la machine régie

Créer **exactement 3 scènes** (noms par défaut attendus par le programme) :

| Scène OBS | Contenu |
|-----------|---------|
| `PLAYER_A` | Flux vidéo du joueur A (Media Source RTMP, Browser VDO.ninja, etc.) |
| `PLAYER_B` | Flux vidéo du joueur B |
| `SPLIT` | Les deux flux côte à côte (layout 50/50 ou picture-in-picture) |

**Activer OBS WebSocket v5** :

1. OBS → **Outils → WebSocket Server Settings**
2. Cocher **Enable WebSocket server**
3. Port : `4455` (défaut)
4. Définir un mot de passe (recommandé)
5. Version : **v5**

La sortie stream (Twitch/YouTube) se configure **uniquement sur cet OBS régie**, pas sur les OBS des joueurs.

---

### Étape 3 — Client LoL sur la machine régie

1. Lancer League of Legends sur la **machine régie**.
2. Rejoindre la partie en **spectateur** (ou y jouer si la régie héberge un compte dans la game).
3. Vérifier que l’API répond (dans un navigateur sur la régie) :
   ```
   https://127.0.0.1:2999/liveclientdata/gamestats
   ```
   *(certificat auto-signé : accepter l’avertissement ou ignorer en HTTPS)*

4. Noter les **noms d’invocateur exacts** (Riot ID) des joueurs A et B tels qu’affichés dans la partie.

---

### Étape 4 — Lancer LoL Auto Director

```bat
pip install -r requirements.txt
python main.py
```

Ou lancer `dist\LoLAutoDirector.exe` après compilation (`build.bat`).

Dans l’interface :

| Champ | Valeur |
|-------|--------|
| **Joueur A (Riot)** | Nom invocateur exact du joueur A |
| **Joueur B (Riot)** | Nom invocateur exact du joueur B |
| **OBS host** | `localhost` (OBS est sur la même machine que la régie) |
| **OBS port** | `4455` |
| **Mot de passe OBS** | Celui défini dans OBS WebSocket |
| **Stratégie de switch** | Voir section stratégies |
| **Délai avant action** | Offset replay (ex. `3` s → kill à 20:00, focus dès 19:57) |

Puis :

1. **Connecter OBS**
2. **Démarrer** le moteur
3. Activer **Mode automatique**

Le statut en bas affiche `OBS ✓ | LoL ✓ | AUTO` quand tout est OK.

---

## Stratégies de switch

| Stratégie | Comportement |
|-----------|--------------|
| **Score (priorité auto)** | Bascule selon scores d’intérêt (kill +100, objectif +120…), priorité des events, split si 2 gros plays proches |
| **Joueur principal** | Caméra sur A (ou B) en permanence ; bascule sur l’autre **seulement** quand il fait une action, puis retour au principal |
| **Dual (alternance)** | Départ aléatoire A ou B ; reste sur le joueur actif jusqu’à ce que l’autre fasse une action |

**Split screen** : si les deux joueurs ont un event majeur (kill, objectif) à moins de 5 s d’écart → scène `SPLIT` pendant 8 s, puis retour au joueur le plus intéressant.

---

## Paramètres de timing

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| Délai avant action | 3 s | Offset « replay instantané » : la régie remonte avant l’event |
| Focus post-event | 12 s | Durée de focus après l’event |
| Split screen | 8 s | Durée de l’écran partagé |

Exemple : kill A à **20:00**, délai 3 s → focus A de **19:57** à **20:12**.

---

## OBS des joueurs (chez eux) — résumé

Chaque joueur configure **son propre OBS** ainsi :

```
Capture du jeu (Window Capture / Game Capture)
        ↓
Encodeur (x264 / NVENC — bitrate adapté à l’upload)
        ↓
Sortie Stream → URL de la machine régie (RTMP / SRT / VDO.ninja)
```

- **Pas** de scènes PLAYER_A / PLAYER_B chez le joueur
- **Pas** de connexion WebSocket OBS vers LoL Auto Director
- Bitrate upload conseillé : **2500–6000 kbps** par joueur selon connexion
- Résolution : 720p60 ou 1080p30 pour limiter la bande passante

---

## Checklist avant le live

- [ ] Serveur ingest ou liens VDO.ninja testés (A et B visibles sur la régie)
- [ ] 3 scènes OBS régie créées : `PLAYER_A`, `PLAYER_B`, `SPLIT`
- [ ] WebSocket OBS v5 activé, mot de passe configuré
- [ ] Client LoL spectateur lancé sur la machine régie, API `127.0.0.1:2999` OK
- [ ] Noms Riot A et B saisis correctement dans LoL Auto Director
- [ ] Test avec les boutons **Test Kill A / B / Split** dans l’interface
- [ ] Stream final régie configuré vers Twitch/YouTube
- [ ] Stratégie et délai avant action choisis

---

## Compilation Windows (.exe)

```bat
build.bat
```

Exécutable produit : `dist\LoLAutoDirector.exe`

---

## Dépannage

| Problème | Cause probable | Solution |
|----------|----------------|----------|
| `LoL ✗` | Pas de client LoL sur la régie | Lancer LoL et spectate la partie |
| `OBS ✗` | WebSocket désactivé ou mauvais mot de passe | Vérifier OBS → WebSocket v5 |
| Events A/B inversés | Noms invocateur incorrects | Vérifier Riot ID exact (casse) |
| Pas de switch | Mode auto désactivé | Cocher **Mode automatique** |
| Flux noir dans OBS | Ingest pas reçu | Tester URL RTMP / VDO.ninja |
| Joueur distant, pas d’events | API locale uniquement | Spectate la game sur la régie |

---

## Sécurité / Vanguard

- Aucune injection, aucune lecture mémoire
- Uniquement **Live Client Data API** (Riot) + **OBS WebSocket v5**
- Compatible Vanguard : l’API Live Client est officiellement exposée par le client LoL

---

## Tests & releases

### Tester la détection des events LoL (sans stream)

Guide complet : **[TESTING.md](TESTING.md)** — **aucun OBS, aucun stream requis**, Practice Tool suffit.

Résumé :

1. Practice Tool → vérifier `https://127.0.0.1:2999/liveclientdata/gamestats`
2. `python scripts/test_live_events.py --player-a "TonPseudo" --watch`
3. Jouer (dégâts / mort / kill bot) → events en direct dans le terminal
4. Ou lancer l’exe → **Démarrer** → `LoL ✓` + **Dernier événement** (ignore `OBS ✗`)

### Télécharger l’exécutable Windows

Releases : **[github.com/RajPorus19/LolCamSwitcher/releases](https://github.com/RajPorus19/LolCamSwitcher/releases)**

Asset : `LoLAutoDirector.exe` (build automatique à chaque tag `v*`).

Version actuelle : **1.0.0** — voir [CHANGELOG.md](CHANGELOG.md).

---

## Structure du projet

```
lol_auto_director/
├── director/     # scoring, priorités, stratégies, timeline
├── lol/          # API Riot Live Client + types d’events
├── buffer/       # buffer temporel replay
├── obs/          # contrôleur OBS WebSocket v5
├── gui/          # interface PySide6
└── engine.py     # orchestration
main.py           # point d’entrée
```

---

## Évolutions prévues

- **Agent relais** : petit programme sur le PC de chaque joueur qui forward les events vers la régie (pour ne plus nécessiter le spectateur local)
- **API Spectator Riot** : récupération d’events sans client LoL ouvert
- **Connexion OBS distante** : champ `OBS host` déjà prévu pour viser une IP autre que `localhost` si l’OBS régie tourne sur un autre PC du LAN
