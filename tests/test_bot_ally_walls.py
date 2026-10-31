"""game/bot.py: an allied bot builds walls by taunts 54 and 55 (#4890), on the map of test_bot_gather (the bot is
player 2, the person is player 1)."""
from test_bot_gather import bot_map

from game.bot import build


def setup(ally=True):
    server, me, b = bot_map()
    if ally:
        for p in ("1", "2"):
            b.g.players.setdefault(p, {})["team"] = 1
    b.g.techs.update(build.AGE_TECHS[:2])                              # the Feudal Age: stone walls
    b.g.stock.update(food=0, wood=5000, gold=0, stone=5000)
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    return me, b, sent


def taunt(me, n, *flares):
    me.flares = [(x, 64, z, me.clock() + 30) for x, z in flares]
    me.taunted = [*getattr(me, "taunted", []), str(n)]


def walls(b):
    return {(s["footprint"][0], s["footprint"][2]) for s in b.g.sites if s["name"] in build.WALLS}


def test_taunt_54_walls_the_tiles_between_two_flares():
    me, b, sent = setup()
    taunt(me, 54, (10.5, 28.5), (15.5, 28.5))
    b.give()
    assert walls(b) == {(x, 28) for x in range(10, 16)}
    assert {s["name"] for s in b.g.sites} == {"STONE_WALL"}
    assert any(v.site is not None for v in b.g.villagers.values())    # a builder goes


def test_one_flare_gives_an_answer_line():
    me, b, sent = setup()
    taunt(me, 54, (10.5, 28.5))
    b.give()
    assert not walls(b) and any("aoe2mc.bot.flare_two" in c for c in sent)


def test_taunt_55_walls_the_town():
    me, b, sent = setup()
    taunt(me, 55)
    b.give()
    cx, cz = b.center()
    tiles = walls(b)
    assert len(tiles) > 8
    assert all(max(abs(x - cx), abs(z - cz)) >= 3 for x, z in tiles)   # around, not on, the town center


def test_no_stone_gives_an_answer_line():
    me, b, sent = setup()
    b.g.stock["stone"] = 0
    taunt(me, 55)
    b.give()
    assert not walls(b) and any("not enough" in c for c in sent)


def test_an_enemy_taunt_changes_nothing():
    me, b, sent = setup(ally=False)
    taunt(me, 54, (10.5, 28.5), (15.5, 28.5))
    taunt(me, 55)
    b.give()
    assert not walls(b)
