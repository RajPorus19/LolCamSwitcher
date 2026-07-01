# Guide de test — détection des events LoL (sans stream)

Ce document sert **uniquement** à vérifier que LoL Auto Director détecte les **actions en live** (kills, morts, dégâts, objectifs…) via l’API Riot Live Client.

## Ce qu’il faut / ce qu’il ne faut pas

| Requis | Pas requis |
|--------|------------|
| Windows (pour l’`.exe`) ou Python | **OBS** |
| League of Legends lancé | **Stream Twitch / YouTube** |
| Être **en partie** (Practice Tool suffit) | **RTMP, VDO.ninja, serveur ingest** |
| Même PC pour LoL + le programme | **Deuxième joueur**, **réseau**, **scènes OBS** |
| | **Connecter OBS** dans l’interface |
| | **Mode automatique** (optionnel pour ce test) |

> **En résumé** : tu lances LoL, tu lances le programme, tu joues — tu observes les events remonter. Rien d’autre.

---

## Prérequis minimaux

| Condition | Obligatoire |
|-----------|-------------|
| League of Legends lancé | Oui |
| **En partie active** (pas le client seul) | Oui |
| Practice Tool | Recommandé (test solo en 2 min) |
| Custom / Ranked / Spectateur | OK aussi |
| OBS / stream | **Non** |
| Vanguard | OK — API officielle locale, aucune injection |

L’API n’est disponible **que pendant une partie** :

```
https://127.0.0.1:2999
```

---

## Parcours complet (5 min, zéro stream)

### Étape 0 — Practice Tool

1. LoL → **Entraînement** → **Practice Tool**
2. Choisis un champion → **Lancer**
3. Attends d’être spawn en map

---

### Test 1 — API dans le navigateur (~30 s)

Sur le **même PC** que LoL, ouvre :

```
https://127.0.0.1:2999/liveclientdata/gamestats
```

**OK** → JSON avec `"gameTime"`, `"gameMode"` :

```json
{
  "gameTime": 42.5,
  "gameMode": "PRACTICETOOL"
}
```

**KO** → connexion refusée → tu n’es pas encore en partie, attends le spawn.

> Certificat auto-signé : accepte l’avertissement du navigateur, c’est normal.

---

### Test 2 — Script de sonde (recommandé, sans GUI)

Depuis le repo cloné :

```bat
pip install -r requirements.txt
python scripts/test_live_events.py --player-a "TonPseudo" --watch
```

Remplace `TonPseudo` par ton nom affiché en partie (voir étape 2 du script).

**OK** :

```
─── Étape 1 : API Live Client ───
  OK  API disponible — temps de jeu : 01:23

─── Étape 2 : Joueurs détectés ───
  • TonPseudo  (Lux, team ORDER)

─── Mode watch (1.0s) — Ctrl+C pour arrêter ───
  Game 02:15 — 0 event(s) total
```

Ensuite **joue** (sbires, tourelle, bots) :

```
  [1] [02:18] A — combat_nearby (+30)  [✓ mappé]
  [2] [02:45] A — low_hp (+40)         [✓ mappé]
  [3] [03:01] A — death (+20)          [✓ mappé]
```

| Message | Signification |
|---------|---------------|
| `OK API disponible` | La détection live fonctionne |
| `FAIL API indisponible` | Pas en partie |
| `✓ mappé` | Pseudo A/B correct |
| `✗ non mappé` | Event vu, mauvais pseudo dans `--player-a` / `--player-b` |

Ctrl+C pour arrêter.

---

### Test 3 — Interface `.exe` ou GUI (sans OBS)

1. Télécharge `LoLAutoDirector.exe` depuis [Releases](https://github.com/RajPorus19/LolCamSwitcher/releases)  
   *ou* `python main.py`
2. Renseigne **Joueur A** = ton pseudo Riot (Joueur B peut rester vide pour un test solo)
3. Clique **Démarrer**
4. **Ignore** : Connecter OBS, mode automatique, stream

Vérifie uniquement :

| Élément UI | Attendu |
|------------|---------|
| Barre de statut | `LoL ✓` (OBS ✗ est **normal**) |
| Temps de jeu | Avance en sync avec la partie |
| Dernier événement | Se met à jour quand tu subis des dégâts, meurs, kill, etc. |
| Score A | Monte quand un event te concerne |

**Actions à faire en Practice Tool** (sans co-joueur) :

| Action in-game | Event attendu |
|----------------|---------------|
| Prendre des dégâts (sbires / tourelle) | `combat_nearby`, `engage` |
| Descendre sous ~25 % HP | `low_hp` |
| Mourir | `death` |
| Kill un champion | `kill` (+ `assist` pour coéquipier A/B) |
| Multikill | `double_kill`, `triple_kill`, `quadra_kill`, `penta_kill` |
| First blood | `first_blood` |
| Kill bot (Practice Tool) | `kill` |
| Farm gros spike CS | `farm` |
| Dragon / Baron / Herald | `dragon`, `baron`, `herald` |
| Tourelle / first brick | `turret`, `first_turret` |
| Inhibiteur | `inhibitor` |
| Ace | `ace` |

Si **Dernier événement** bouge → la détection live est **validée**. Tu peux fermer l’app.

---

### Test 4 — Events bruts Riot (debug)

Pendant la partie :

```
https://127.0.0.1:2999/liveclientdata/eventdata
```

Liste JSON des events Riot (`ChampionKill`, `ChampionDeath`, etc.).  
Si cette page se remplit mais pas l’app → problème de mapping pseudo (Test 2 étape 2).

Liste des joueurs :

```
https://127.0.0.1:2999/liveclientdata/playerlist
```

Copie le `summonerName` **exact** dans Joueur A.

---

## Checklist validation (sans stream)

Coche tout — **aucun item OBS/stream** :

- [ ] Practice Tool (ou autre partie) lancé
- [ ] `gamestats` répond en navigateur
- [ ] `test_live_events.py --watch` → `OK API disponible`
- [ ] Au moins **1 event** remonte en jouant (`combat_nearby` minimum)
- [ ] Event `✓ mappé` avec le bon pseudo
- [ ] GUI / exe → `LoL ✓` + **Dernier événement** réactif

**Si tout est coché → la détection live fonctionne.** Le setup stream/OBS est un sujet séparé ([README.md](README.md)).

---

## Dépannage

| Symptôme | Cause | Fix |
|----------|-------|-----|
| `LoL ✗` | Pas en partie | Practice Tool, attendre spawn |
| API OK, 0 event | Rien ne s’est passé | Prends des dégâts / meurs / kill un bot |
| Events `non mappés` | Mauvais pseudo | Copier depuis `playerlist` ou étape 2 du script |
| `OBS ✗` en statut | OBS non lancé | **Normal pour ce test — ignore** |
| exe ne voit pas LoL | Pas le même PC | LoL et l’exe sur **la même machine** |
| `eventdata` vide | Début de partie | Joue 1–2 min, provoque des actions |
| Antivirus bloque l’exe | PyInstaller | Exception pour `LoLAutoDirector.exe` |

---

## Ce qui n’est PAS couvert par ce guide

| Sujet | Où le tester |
|-------|--------------|
| Switch scènes OBS | [README.md](README.md) — setup régie |
| Stream RTMP / deux POV distants | [README.md](README.md) — architecture réseau |
| Boutons **Test Kill A/B** dans la GUI | Logique régie **fictive** — ne teste pas l’API Riot |
| Scoring / stratégies / timeline | `python -m pytest tests/ -v` (sans LoL) |

Les boutons **Test Kill A / B / Split** simulent des events en mémoire pour tester la régie **sans** partie LoL. Utile pour OBS plus tard, **pas** pour valider la détection live.

---

## Tests automatisés (sans LoL, sans stream)

Logique interne uniquement (scores, stratégies, timeline) :

```bat
pip install pytest
python -m pytest tests/ -v
```

Ne remplace pas les tests live ci-dessus — ne touche pas à l’API Riot.

---

## Journal de partie (logs)

Chaque partie génère un fichier :

```
%LOCALAPPDATA%\LoLAutoDirector\logs\game_2026-07-01_143052.log
```

Exemple de lignes :

```
[2026-07-01 14:30:52] [GAME 02:15] EVENT        Player A — kill (+100) | target PLAYER_A | focus 02:12→02:27 | pre-delay -3s
[2026-07-01 14:30:52] [GAME 02:12] FOCUS        Director focus → PLAYER_A (trigger=event)
[2026-07-01 14:30:52] [GAME 02:12] CAMERA       Camera switched to PLAYER_A (scene: PLAYER_A) at game time 02:12 [event]
```

Consultable en direct dans la GUI → **Journal de partie** (bouton **Live** ou sélection d’un ancien fichier).

---

## Récap visuel

```
Practice Tool (LoL)
       │
       │  API locale 127.0.0.1:2999
       ▼
┌──────────────────────────┐
│  test_live_events.py     │  ← terminal, events en direct
│  ou                      │
│  LoLAutoDirector.exe     │  ← GUI, « Dernier événement »
└──────────────────────────┘
       │
       ✗ PAS de stream
       ✗ PAS d'OBS
       ✗ PAS de RTMP
```
