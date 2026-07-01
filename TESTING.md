# Guide de test — détection des events LoL

Ce document explique comment vérifier que **LoL Auto Director** (`.exe` ou Python) détecte bien les événements en direct depuis l’API Riot Live Client.

---

## Prérequis

| Condition | Obligatoire |
|-----------|-------------|
| Windows | Oui (pour l’`.exe`) |
| League of Legends lancé | Oui |
| **En partie active** (pas seulement le client) | Oui |
| Practice Tool / Custom / Ranked / Spectateur | Tous fonctionnent |
| Vanguard | OK — aucune injection, API officielle locale |

L’API Live Client n’est disponible **que pendant une partie** :

```
https://127.0.0.1:2999
```

---

## Test 1 — Vérifier l’API dans le navigateur (30 s)

1. Lance **League of Legends**.
2. Entre en **Practice Tool** (entraînement) — le plus simple pour tester seul.
3. Une fois en jeu, ouvre dans le navigateur (sur le même PC) :

   ```
   https://127.0.0.1:2999/liveclientdata/gamestats
   ```

4. **Résultat attendu** : JSON avec `"gameTime"`, `"gameMode"`, etc.

   ```json
   {
     "gameTime": 42.5,
     "gameMode": "PRACTICETOOL",
     ...
   }
   ```

5. Si **connexion refusée** ou page blanche → le client LoL n’est pas en partie ou l’API n’est pas encore prête. Attends le spawn en map.

> Certificat auto-signé : le navigateur affiche un avertissement — c’est normal, accepte pour le test.

---

## Test 2 — Script de sonde (recommandé)

Depuis le repo (ou avec Python installé à côté de l’exe) :

```bat
pip install -r requirements.txt
python scripts/test_live_events.py --watch
```

Ou avec les noms Riot de tes joueurs :

```bat
python scripts/test_live_events.py --player-a "TonPseudo" --player-b "AutrePseudo" --watch
```

### Résultat attendu

```
LoL Auto Director — test Live Client API
============================================
─── Étape 1 : API Live Client ───
  OK  API disponible — temps de jeu : 01:23

─── Étape 2 : Joueurs détectés ───
  • TonPseudo  (Lux, team ORDER)
  • ...

─── Mode watch (1.0s) — Ctrl+C pour arrêter ───
  Game 02:15 — 0 event(s) total
```

Ensuite, **tue un sbire ou un mannequin** en Practice Tool, ou fais un kill en custom :

```
  [1] [02:18] A — kill (+100)  [✓ mappé]
  Game 02:20 — 1 event(s) total
```

| Message | Signification |
|---------|---------------|
| `OK API disponible` | L’exe pourra lire LoL |
| `FAIL API indisponible` | Pas en partie — retourne en game |
| `✓ mappé` | Le nom Riot correspond à `--player-a` ou `--player-b` |
| `✗ non mappé` | Event détecté mais nom joueur incorrect dans la config |

---

## Test 3 — Interface graphique (`.exe`)

1. Lance `LoLAutoDirector.exe` (ou `python main.py`).
2. Renseigne **Joueur A** et **Joueur B** (noms exacts visibles en partie).
3. Clique **Démarrer** (OBS n’est pas obligatoire pour ce test).
4. Regarde la barre de statut en bas :

   | Statut | Signification |
   |--------|---------------|
   | `LoL ✓` | API Live Client détectée |
   | `LoL ✗` | Pas en partie ou API inaccessible |

5. En Practice Tool, provoque des actions (kill, mort, dégâts).
6. Vérifie que **Dernier événement** se met à jour dans le panneau « État de la régie ».

### Boutons de test sans partie live

Les boutons **Test Kill A / B / Split** injectent des events fictifs pour valider la logique de régie et OBS **sans** client LoL. Ils ne testent **pas** l’API Riot.

---

## Test 4 — Valider le mapping joueur A / B

1. En `--watch`, note le nom exact affiché à l’étape 2 (`summonerName`).
2. Copie-le **tel quel** dans l’interface (casse incluse).
3. Refais une action avec ce compte → l’event doit afficher `✓ mappé` et le bon focus.

Pour lister les events bruts Riot :

```
https://127.0.0.1:2999/liveclientdata/eventdata
```

---

## Test 5 — `.exe` vs Python (parité)

| Test | Python | `.exe` |
|------|--------|--------|
| API `127.0.0.1:2999` | `test_live_events.py` | GUI statut `LoL ✓` |
| Events kill/objectif | `--watch` | Champ « Dernier événement » |
| Stratégies / délai | GUI | GUI |
| OBS switch | Connecter OBS + auto | Idem |

L’`.exe` embarque la même logique que `main.py` — si le script Python voit les events, l’exe aussi.

---

## Scénario Practice Tool pas à pas

1. LoL → **Entraînement** → Practice Tool → choisir un champion → lancer.
2. `python scripts/test_live_events.py --watch --player-a "TonPseudo"`
3. Attendre spawn → vérifier `LoL ✓` / `OK API disponible`.
4. Tuer des sbires / mourir contre une tourelle.
5. Observer les events remonter (au minimum `combat_nearby`, `low_hp`, `death`).
6. Lancer l’exe → **Démarrer** → confirmer « Dernier événement ».

> Les kills sur champions nécessitent des bots ou un co-joueur ; les events de dégâts/mort fonctionnent déjà seuls.

---

## Dépannage

| Symptôme | Cause | Fix |
|----------|-------|-----|
| `LoL ✗` permanent | Pas en partie | Practice Tool ou custom |
| API OK, 0 event | Rien ne s’est passé | Provogue kill/mort/dégâts |
| Events `non mappés` | Mauvais pseudo | Copier le nom depuis l’étape 2 du script |
| API OK en Python, pas en exe | Pare-feu / autre PC | L’exe doit tourner **sur le même PC que LoL** |
| `eventdata` vide longtemps | Début de partie | Normal — events apparaissent après les premières actions |
| Antivirus bloque l’exe | PyInstaller | Ajouter une exception pour `LoLAutoDirector.exe` |

---

## Checklist rapide avant un live

- [ ] `test_live_events.py --watch` → `OK API disponible`
- [ ] Au moins 1 event `✓ mappé` en conditions réelles
- [ ] GUI → `LoL ✓` + « Dernier événement » réactif
- [ ] Noms Riot A et B validés
- [ ] (Optionnel) OBS connecté + test bouton Kill A change la scène

---

## Tests automatisés (logique régie, sans LoL)

```bat
pip install pytest
python -m pytest tests/ -v
```

Ces tests couvrent scoring, stratégies et timeline — **pas** l’API Live Client (nécessite une vraie partie).
