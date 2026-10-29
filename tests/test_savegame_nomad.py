"""A saved game keeps the Nomad start of a player (#2986, epic #2253): the first town center gives its bonus once, also
after a save and a load (savegame.NOMAD: `later` and `nomad`). Fake server of test_nomad_start."""
import json
import math

from test_gather import FakeServer, grid

from game import build, gather, savegame

UNITS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 1.5]}]
FIRST, SECOND = (6, 10, 6, 10), (0, 4, 10, 14)


def game(civ):
    data = grid([[64] * 16 for _ in range(16)], UNITS)
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = FakeServer({})
    return server, gather.Gather(server, data)


def town_center(g, rect):
    """Found a town center and let it rise to the end: the bonus of a Nomad start comes with the first one."""
    g.stock.update(wood=1000, stone=1000)
    return build.rise(g, build.found(g, "TOWN_CENTER", rect), math.inf)


def saved(g):
    return json.loads(json.dumps(savegame.dump(g), sort_keys=True))


def bonus(server, start):
    """The scoreboard bonuses and horse summons that the server got after the first start commands."""
    return [c for c in server.log[start:] if c.startswith(("scoreboard players add", "summon minecraft:horse"))]


def test_a_load_after_the_first_town_center_gives_no_second_bonus():
    server, g = game("TUPI")
    assert town_center(g, FIRST) and bonus(server, 0)
    server_h, h = game("TUPI")
    savegame.load(h, saved(g))
    assert h.later == {} and h.nomad is False
    start = len(server_h.log)
    assert town_center(h, SECOND)
    assert bonus(server_h, start) == []


def test_a_huns_load_after_the_first_town_center_summons_no_second_horse():
    server, g = game("HUNS")
    assert town_center(g, FIRST) and len(bonus(server, 0)) == 1
    server_h, h = game("HUNS")
    savegame.load(h, saved(g))
    start = len(server_h.log)
    assert town_center(h, SECOND)
    assert bonus(server_h, start) == []


def test_a_load_before_the_first_town_center_keeps_the_bonus_once():
    _, g = game("TUPI")
    server_h, h = game("TUPI")
    savegame.load(h, saved(g))
    assert h.nomad is True and h.later == g.later and h.later["gold"] > 0
    gold = h.later["gold"]
    assert town_center(h, FIRST)
    assert f"scoreboard players add Gold aoe_res {gold}" in server_h.log
    start = len(server_h.log)
    assert town_center(h, SECOND)
    assert bonus(server_h, start) == []
