"""game/bot.py: an allied bot builds a navy by taunts 34 and 75, stops by 35 and deletes the warships above FLEET by
71 (#4883), on the map of test_bot_gather with water near the town of the bot (player 2)."""
import build  # noqa: E402
import gather  # noqa: E402
import train  # noqa: E402
from test_bot_gather import bot_map
from test_gather import grid

import game.bot as bot


def setup(water=True, ally=True):
    server, me, b = bot_map()
    if water:                                                      # a sea at x >= 28: the shore is near the town
        data = grid([[("-" if x >= 28 else 64) for x in range(32)] for _ in range(32)], b.g.data["objects"])
        b.g.map.ground = gather.Map(data).ground
    for p, team in (("1", 1), ("2", 1 if ally else 2)):
        b.g.players.setdefault(p, {})["team"] = team
    b.g.techs.update(build.AGE_TECHS)
    b.g.stock.update(food=2000, wood=2000, gold=2000, stone=0)
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    return me, b, sent


def taunt(me, n):
    me.taunted = [*getattr(me, "taunted", []), str(n)]


def docks(b):
    return [s for s in b.g.sites if s["name"] == "DOCK"]


def ships(b):
    return [e["name"] for r, h in train.homes(b.g).items() if h == "DOCK" for e in b.g.queues.get(r, [])]


def test_taunt_34_gives_a_dock_and_warships_and_35_stops_them():
    me, b, _ = setup()
    taunt(me, 34)
    b.give()
    b.build()
    x0, x1, z0, z1 = docks(b)[0]["footprint"]
    assert len(docks(b)) == 1 and all(b.g.map.ground[z][x] is None for x in range(x0, x1) for z in range(z0, z1))
    docks(b)[0]["done"] = True
    b.recruit()
    assert ships(b) and ships(b)[0] == b.soldiers("DOCK")[0]
    b.g.queues.clear()
    taunt(me, 35)
    b.give()
    b.recruit()
    assert not ships(b)


def test_no_water_gives_one_line_and_no_dock():
    me, b, sent = setup(water=False)
    taunt(me, 75)
    b.give()
    b.give()
    b.build()
    assert not docks(b) and sum("no water" in c for c in sent) == 1


def test_an_enemy_taunt_changes_nothing():
    me, b, _ = setup(ally=False)
    taunt(me, 34)
    b.give()
    assert b.navy is None and not docks(b)


def test_taunt_71_deletes_the_warships_above_fleet(monkeypatch):
    me, b, sent = setup()
    monkeypatch.setattr(bot, "FLEET", 1)
    ship = b.soldiers("DOCK")[0]
    b.g.soldiers.update({"w1": ship, "w2": ship})
    taunt(me, 71)
    b.give()
    assert "kill w2" in sent and "kill w1" not in sent
