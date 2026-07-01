"""Unit tests for Riot event mapping."""

from lol_auto_director.lol.api import RiotLiveClientAPI
from lol_auto_director.lol.events import EventType, multikill_type


def _api() -> RiotLiveClientAPI:
    return RiotLiveClientAPI(player_a_name="PlayerA", player_b_name="PlayerB")


class TestMultikillType:
    def test_streaks(self):
        assert multikill_type(2) == EventType.DOUBLE_KILL
        assert multikill_type(3) == EventType.TRIPLE_KILL
        assert multikill_type(4) == EventType.QUADRA_KILL
        assert multikill_type(5) == EventType.PENTA_KILL
        assert multikill_type(7) == EventType.PENTA_KILL


class TestRiotEventMapping:
    def test_champion_kill_with_assists(self):
        api = _api()
        raw = {
            "EventName": "ChampionKill",
            "EventTime": 100.0,
            "KillerName": "PlayerA",
            "VictimName": "Enemy",
            "Assisters": ["PlayerB"],
        }
        events = api._map_riot_event(raw)
        types = [e.type for e in events]
        assert EventType.KILL in types
        assert EventType.ASSIST in types
        assert events[0].player == "A"
        assert any(e.player == "B" and e.type == EventType.ASSIST for e in events)

    def test_multikill_triple(self):
        api = _api()
        events = api._map_riot_event(
            {
                "EventName": "Multikill",
                "EventTime": 200.0,
                "KillerName": "PlayerB",
                "KillStreak": 3,
            }
        )
        assert len(events) == 1
        assert events[0].type == EventType.TRIPLE_KILL
        assert events[0].player == "B"

    def test_dragon_and_baron(self):
        api = _api()
        dragon = api._map_riot_event(
            {
                "EventName": "DragonKill",
                "EventTime": 300.0,
                "KillerName": "PlayerA",
                "DragonType": "Fire",
            }
        )
        baron = api._map_riot_event(
            {
                "EventName": "BaronKill",
                "EventTime": 400.0,
                "KillerName": "PlayerB",
            }
        )
        assert dragon[0].type == EventType.DRAGON
        assert baron[0].type == EventType.BARON

    def test_first_blood_and_ace(self):
        api = _api()
        fb = api._map_riot_event(
            {
                "EventName": "FirstBlood",
                "EventTime": 50.0,
                "Recipient": "PlayerA",
            }
        )
        ace = api._map_riot_event(
            {
                "EventName": "Ace",
                "EventTime": 600.0,
                "Acer": "PlayerB",
                "AcingTeam": "ORDER",
            }
        )
        assert fb[0].type == EventType.FIRST_BLOOD
        assert ace[0].type == EventType.ACE

    def test_inhibitor_herald_first_turret(self):
        api = _api()
        inhib = api._map_riot_event(
            {
                "EventName": "InhibKilled",
                "EventTime": 500.0,
                "KillerName": "PlayerA",
            }
        )
        herald = api._map_riot_event(
            {
                "EventName": "HeraldKill",
                "EventTime": 450.0,
                "KillerName": "PlayerB",
            }
        )
        first = api._map_riot_event(
            {
                "EventName": "FirstBrick",
                "EventTime": 350.0,
                "KillerName": "PlayerA",
            }
        )
        assert inhib[0].type == EventType.INHIBITOR
        assert herald[0].type == EventType.HERALD
        assert first[0].type == EventType.FIRST_TURRET
