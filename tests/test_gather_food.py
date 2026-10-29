"""game/gather.py: villagers gather food from fruit bushes (#391). The fast tests use a fake server; the mc test a real one."""
import contextlib
import io
import json
import math
import time

import pytest
from test_gather import FakeServer, grid

from game import gather, run

BUSHES = [(10, 10), (14, 10)]


def food_map():
    """A flat 20 × 20 map (tile size 1): a town center of player 1, a villager and two fruit bushes."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    objects += [{"kind": "other", "name": "FRUIT_BUSH", "tile": [x + 0.5, z + 0.5]} for x, z in BUSHES]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    return server, gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects), carry=10, chop=0.25, start={}).setup()


def food(server):
    return sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Food aoe_res"))


def test_a_click_on_a_fruit_bush_sends_a_forager():
    server, g = food_map()
    assert g.map.bushes == dict.fromkeys(BUSHES, gather.BUSH_FOOD) and not g.map.trees
    eye = (10.5, 65.62, 14.5)
    assert g.map.pick_tree(eye, gather.direction(180, 20)) == (10, 10)    # look north and down at the bush
    assert g.map.pick_tree((10.5, 70, 14.5), gather.direction(180, 0)) is None    # high over the bush
    g.select("v")
    g.send((10, 10))
    v = g.villagers["v"]
    assert v.state == "to_tree" and v.res == "food" and v.tree == (10, 10)
    assert 'data merge entity v {VillagerData:{profession:"minecraft:farmer"},Offers:{Recipes:[]}}' in server.log


def test_villagers_forage_a_bush_empty_and_go_to_the_next_one():
    server, g = food_map()
    g.select("v")
    g.send((10, 10))
    for _ in range(3000):
        g.step()
        if g.map.bushes[(10, 10)] == 0 and g.villagers["v"].tree == (14, 10):
            break
    v = g.villagers["v"]
    assert g.map.bushes[(10, 10)] == 0 and v.tree == (14, 10) and v.state == "to_tree"
    assert food(server) == gather.BUSH_FOOD and g.stock["food"] == gather.BUSH_FOOD and g.wood == 0
    fills = [c for c in server.log if c.startswith("fill 10 ") and "replace minecraft:sweet_berry_bush" in c]
    assert [c.split()[7] for c in fills] == ["minecraft:sweet_berry_bush[age=2]", "minecraft:dead_bush"]
    tc = set().union(*g.map.drops["food"])
    cells = [(math.floor(float(c.split()[2])), math.floor(float(c.split()[4]))) for c in server.log if c.startswith("tp ")]
    assert any(max(abs(x - a), abs(z - b)) == 1 for x, z in cells for a, b in tc)    # it went to the town center


def test_a_villager_stops_when_no_bush_has_food():
    server, g = food_map()
    g.map.bushes[(14, 10)] = 0
    g.select("v")
    g.send((10, 10))
    for _ in range(3000):
        g.step()
    assert g.villagers["v"].state == "idle" and g.stock["food"] == gather.BUSH_FOOD


@pytest.mark.mc
def test_villager_forages_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=8.5)
    um.add_unit(scenarios.PlayerId.GAIA, OtherInfo.FRUIT_BUSH.ID, x=10.5, y=10.5)
    src = str(tmp_path / "food.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while True:
            g = gather.Gather(game, data, tick=0.05, carry=10, chop=0.01, start={}).setup()
            if g.villagers:
                break
            assert time.time() < end, "the villager did not load"
            time.sleep(1)
        uuid, = g.villagers
        bush, = g.map.bushes
        g.select(uuid)
        g.send(bush)
        assert 'profession: "minecraft:farmer"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 180                                        # 13 trips at the AoE2 walk speed (#437)
        while g.map.bushes[bush] > 0 or g.villagers[uuid].state != "idle":
            assert time.time() < end, "the bush is not empty after 180 s"
            g.step()
        assert f"has {gather.BUSH_FOOD} " in game.command("scoreboard players get Food aoe_res")
        T = g.map.T
        x, z = bush[0] * T, bush[1] * T                                # a berry bush of the ring (#590)
        y = min(g.map.y(*c) for c in g.map.around(g.map.cells(bush)))
        assert "passed" in game.command(f"execute if block {x} {y} {z} minecraft:dead_bush"), "no dead bush"
        mid = int((bush[0] + 0.5) * T), int((bush[1] + 0.5) * T)      # the leaves in the middle: free now (#602)
        assert "passed" in game.command(f"execute if block {mid[0]} {y} {mid[1]} minecraft:air"), "not free"
