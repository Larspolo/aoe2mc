"""game/gather.py: the start bonuses of the town center (#2293, AoE2 DE wiki): Tupi get more of each resource with the
first town center (civs.TOWN_CENTER), Gurjaras start with forage bushes next to it (the key "bushes"). Fake server."""
import math

from game import build, civs, gather

from test_gather import FakeServer, grid

UNITS = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [1.5, 1.5]}]
TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [8.0, 8.0], "footprint": [6, 6, 10, 10]}
TUPI = civs.TOWN_CENTER.get("TUPI", {})


def game(civ, objects):
    data = grid([[64] * 16 for _ in range(16)], objects)
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    data["level_height"] = 1
    server = FakeServer({})
    return server, gather.Gather(server, data)


def test_tupi_start_with_more_of_each_resource_with_a_town_center():
    assert game("TUPI", UNITS + [TC])[1].stock == {r: v + TUPI.get(r, 0) for r, v in gather.START.items()}


def test_a_tupi_nomad_gets_the_bonus_when_its_first_town_center_is_complete():
    server, g = game("TUPI", UNITS)
    first = dict(g.stock)
    g.stock.update(wood=1000, stone=1000)
    site = build.found(g, "TOWN_CENTER", (6, 10, 6, 10))
    assert not build.rise(g, site, 1) and g.stock["food"] == first["food"]
    assert build.rise(g, site, math.inf) and g.stock["food"] == first["food"] + TUPI["food"]
    assert g.stock["gold"] == first["gold"] + TUPI["gold"]
    assert f"scoreboard players add Gold aoe_res {TUPI['gold']}" in server.log
    build.rise(g, build.found(g, "TOWN_CENTER", (0, 4, 10, 14)), math.inf)   # only the first one
    assert g.stock["gold"] == first["gold"] + TUPI["gold"]


def test_other_civilizations_get_no_town_center_bonus():
    server, g = game("BRITONS", UNITS)
    site = build.found(g, "TOWN_CENTER", (6, 10, 6, 10))
    food = g.stock["food"]
    build.rise(g, site, math.inf)
    assert g.stock["food"] == food


def test_gurjaras_start_with_their_bushes_next_to_the_town_center():
    server, g = game("GURJARAS", UNITS + [TC])
    g.setup()
    n, food = civs.BY_KEY["bushes"]["GURJARAS"]
    assert len(g.map.bushes) == n and set(g.map.bushes.values()) == {food} and (7, 10) in g.map.bushes   # the south side
    assert all(c in g.map.blocked for t in g.map.bushes for c in g.map.cells(t))
    assert "setblock 7 64 10 minecraft:sweet_berry_bush[age=3]" in server.log
    assert "setblock 7 63 10 minecraft:grass_block" in server.log


def test_no_start_bushes_for_other_civilizations_or_without_a_town_center():
    for civ, objects in (("BRITONS", UNITS + [TC]), ("GURJARAS", UNITS)):
        server, g = game(civ, objects)
        g.setup()
        assert g.map.bushes == {}
