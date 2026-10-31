"""game/bot.py: an allied bot builds at the flare of its ally by taunts 49, 50, 52 and 53 (#4889), on the map of
test_bot_gather (the bot is player 2, the person is player 1)."""
import math

import flare  # noqa: E402
from test_bot_gather import bot_map

from game import bot
from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)

SPOT = (14, 64, 14)                                                    # a free place between the two towns


def setup(monkeypatch, team=1):
    server, me, b = bot_map()
    b.g.players.setdefault("1", {})["team"] = team
    b.g.players.setdefault("2", {})["team"] = 1
    monkeypatch.setattr(build, "locked", lambda g, n: None)           # the age of each building
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    sent, command = [], b.g.command
    monkeypatch.setattr(b.g, "command", lambda c: sent.append(c) or command(c))
    flare.put(me, "Player 1", *SPOT)
    return me, b, sent


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]


def sites(b, name):
    return [s for s in b.g.sites if s["name"] == name]


def test_taunt_52_puts_a_market_near_the_flare_with_a_builder(monkeypatch):
    me, b, sent = setup(monkeypatch)
    taunt(me, 52)
    b.give()
    s, = sites(b, "MARKET")
    x0, x1, z0, z1 = s["footprint"]
    assert math.dist(((x0 + x1) / 2, (z0 + z1) / 2), (SPOT[0], SPOT[2])) <= 4
    assert any(v.site is s for v in b.g.villagers.values())


def test_too_few_resources_give_an_answer_and_no_site(monkeypatch):
    me, b, sent = setup(monkeypatch)
    b.g.stock.update(food=0, wood=0, gold=0, stone=0)
    taunt(me, 52)
    b.give()
    assert not sites(b, "MARKET") and any("tellraw @a[team=p1]" in c and "cannot build" in c for c in sent)


def test_each_taunt_has_its_buildings(monkeypatch):
    me, b, sent = setup(monkeypatch)
    for n in bot.BUILD_AT:
        taunt(me, n)
    b.give()
    assert {s["name"] for s in b.g.sites} >= {c[0] for cs in bot.BUILD_AT.values() for c in cs if len(c) == 1}


def test_an_enemy_taunt_changes_nothing(monkeypatch):
    me, b, sent = setup(monkeypatch, team=2)
    taunt(me, 52)
    b.give()
    assert not sites(b, "MARKET")
