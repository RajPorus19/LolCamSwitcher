"""Probe Riot Live Client API — verify LoL game events are reachable.

Usage (Windows, during an active game or Practice Tool):
    python scripts/test_live_events.py
    python scripts/test_live_events.py --player-a "MonPseudo" --player-b "AutrePseudo"
    python scripts/test_live_events.py --watch
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Allow running from repo root without install
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lol_auto_director.lol.api import RiotLiveClientAPI
from lol_auto_director.lol.events import GameEvent


def check_api(api: RiotLiveClientAPI) -> bool:
    print("─── Étape 1 : API Live Client ───")
    if api.is_available():
        game_time = api.get_game_time()
        minutes = int(game_time // 60)
        seconds = int(game_time % 60)
        print(f"  OK  API disponible — temps de jeu : {minutes:02d}:{seconds:02d}")
        return True
    print("  FAIL  API indisponible (https://127.0.0.1:2999)")
    print()
    print("  Vérifiez que :")
    print("    • League of Legends est lancé")
    print("    • Vous êtes EN PARTIE (Practice Tool, custom ou ranked)")
    print("    • Le client n'est pas bloqué par un pare-feu local")
    return False


def list_players(api: RiotLiveClientAPI) -> None:
    print()
    print("─── Étape 2 : Joueurs détectés ───")
    players = api.get_all_players()
    if not players:
        print("  Aucun joueur — attendez le chargement de la partie.")
        return
    for p in players:
        name = p.get("summonerName") or p.get("riotId") or "?"
        team = p.get("team", "?")
        champ = p.get("championName", "?")
        print(f"  • {name}  ({champ}, team {team})")


def poll_once(api: RiotLiveClientAPI, player_a: str, player_b: str) -> list[GameEvent]:
    print()
    print("─── Étape 3 : Poll événements ───")
    events = api.poll_events()
    if not events:
        print("  Aucun nouvel événement (normal si rien ne s'est passé).")
        print("  Faites un kill en Practice Tool pour tester.")
    else:
        for e in events:
            mapped = "✓ mappé" if e.player in ("A", "B") else "✗ non mappé (nom Riot incorrect ?)"
            print(f"  {e}  [{mapped}]")
    return events


def watch(api: RiotLiveClientAPI, interval: float) -> None:
    print()
    print(f"─── Mode watch ({interval}s) — Ctrl+C pour arrêter ───")
    seen = 0
    while True:
        if not api.is_available():
            print("\r  En attente de partie LoL…", end="", flush=True)
        else:
            gt = api.get_game_time()
            events = api.poll_events()
            for e in events:
                seen += 1
                print(f"\n  [{seen}] {e}")
            print(
                f"\r  Game {int(gt // 60):02d}:{int(gt % 60):02d} — {seen} event(s) total",
                end="",
                flush=True,
            )
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test détection events LoL Live Client API")
    parser.add_argument("--player-a", default="", help="Nom invocateur joueur A")
    parser.add_argument("--player-b", default="", help="Nom invocateur joueur B")
    parser.add_argument("--watch", action="store_true", help="Poll en continu")
    parser.add_argument("--interval", type=float, default=1.0, help="Intervalle watch (s)")
    args = parser.parse_args()

    print("LoL Auto Director — test Live Client API")
    print("=" * 44)

    api = RiotLiveClientAPI(
        player_a_name=args.player_a,
        player_b_name=args.player_b,
    )

    if not check_api(api):
        return 1

    list_players(api)

    if args.watch:
        try:
            watch(api, args.interval)
        except KeyboardInterrupt:
            print("\nArrêt.")
        return 0

    poll_once(api, args.player_a, args.player_b)

    print()
    print("─── Résumé ───")
    print("  Si l'API est OK mais aucun event ne remonte :")
    print("    → provoquez un kill / mort en Practice Tool")
    print("    → relancez avec --watch pour voir les events en direct")
    print("  Si les events sont « non mappés » :")
    print("    → vérifiez --player-a / --player-b (nom exact in-game)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
