"""game/bot.py: an allied bot trains the units that counter the army of its foe by taunt 56 and stops by 57 (#4885)."""
import combat
from test_bot_tech_reserve import barracks_bot

from game import bot


def trained(b):
    names = [e["name"] for q in b.g.queues.values() for e in q if e["name"] != "VILLAGER_MALE"]
    b.g.queues.clear()
    return names


def setup(monkeypatch):
    b = barracks_bot({r: 5000 for r in bot.SHARE})
    me, enemy = b.share, type("Side", (), {})()
    enemy.player, enemy.soldiers = 3, {"k1": "KNIGHT"}
    for p, team in (("1", 1), ("2", 1), ("3", 2)):
        b.g.players.setdefault(p, {})["team"] = team
    monkeypatch.setattr(bot.build, "sides", lambda g: [me, b.g, enemy])
    monkeypatch.setattr(b.g, "seen_tiles", lambda *a: {(20, 20)})
    monkeypatch.setattr(b.g, "positions", lambda us: {u: (20.5, 64.0, 20.5) for u in us})
    b.foe = 3
    return b, me, enemy


def best(b):
    """The unit of the test data with the largest bonus against cavalry that the Barracks trains."""
    return max(b.soldiers("BARRACKS"), key=lambda n: combat.stats(n).bonus.get("cavalry", 0))


def test_taunt_56_trains_counter_units_and_57_stops(monkeypatch):
    b, me, enemy = setup(monkeypatch)
    first = b.soldiers("BARRACKS")[0]
    assert combat.stats(best(b)).bonus.get("cavalry", 0) > combat.stats(first).bonus.get("cavalry", 0)
    enemy.taunted = ["56"]                                     # an enemy taunt changes nothing
    b.give()
    b.recruit()
    assert set(trained(b)) == {first}
    me.taunted = ["56"]
    b.give()
    b.recruit()
    assert set(trained(b)) == {best(b)}
    me.taunted = ["56", "57"]
    b.give()
    b.recruit()
    assert set(trained(b)) == {first}

