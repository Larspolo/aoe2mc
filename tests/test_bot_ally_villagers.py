"""game/bot.py: an allied bot changes its villager count by taunts 33, 32 and 70 (#4882), on the map of
test_bot_gather (the bot is player 2, the person is player 1); an enemy bot ignores them."""
from test_bot_ally_tribute import taunt
from test_bot_gather import bot_map

from game.bot import EXTRA, build  # noqa: F401  (puts game/ on the path for the plain names)


def setup(monkeypatch, team=1):
    server, me, b = bot_map()
    b.g.players.setdefault("1", {})["team"] = 1
    b.g.players.setdefault("2", {})["team"] = team
    sent = []
    command = b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: sent.append(c) or command(c))
    return me, b, sent


def test_taunt_33_of_an_ally_raises_the_count_and_answers(monkeypatch):
    me, b, sent = setup(monkeypatch)
    n = b.villagers
    taunt(me, 33)
    b.staff()
    b.answer()
    assert b.villagers == n + EXTRA
    assert sum(c.startswith("tellraw @a[team=p2]") for c in sent) == 1


def test_taunt_33_of_an_enemy_changes_nothing(monkeypatch):
    me, b, sent = setup(monkeypatch, team=2)
    n = b.villagers
    taunt(me, 33)
    b.staff()
    b.answer()
    assert b.villagers == n and not any(c.startswith("tellraw") for c in sent)


def test_taunt_32_stops_the_villagers(monkeypatch):
    me, b, sent = setup(monkeypatch)
    b.villagers = 99
    taunt(me, 32)
    b.staff()
    assert b.villagers == len(b.g.villagers)
    b.g.stock.update(food=9999, wood=9999, gold=9999, stone=9999)
    b.recruit()
    assert not any(e["name"] == "VILLAGER_MALE" for q in b.g.queues.values() for e in q)


def test_taunt_70_deletes_only_the_villagers_above_the_count(monkeypatch):
    me, b, sent = setup(monkeypatch)
    have = sorted(b.g.villagers)
    assert len(have) >= 2
    b.villagers = 1
    taunt(me, 70)
    b.staff()
    killed = {c.split()[2] for c in sent if c.endswith("run kill @s") and "on vehicle" not in c}
    assert killed == set(have[1:])
