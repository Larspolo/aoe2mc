"""game/gather.py: villagers gather food from farms (#392). The fast tests use a fake server; the mc test a real one."""
import contextlib
import io
import json
import time

import pytest
from test_gather import FakeServer, grid

from game import gather, run

FARMS = {(10, 10): [9, 9, 12, 12], (16, 10): [15, 9, 18, 12]}       # farm tile -> footprint [x0, z0, x1, z1]


def farm_map(villagers=("v",)):
    """A flat 24 × 24 map (tile size 1): a town center and a mill of player 1, villagers and two farms."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "MILL", "player": 1, "tile": [13, 15], "footprint": [12, 14, 14, 16]}]
    objects += [{"kind": "building", "name": "FARM", "player": 1, "tile": [t[0] + 0.5, t[1] + 0.5], "footprint": f}
                for t, f in FARMS.items()]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": u, "tile": [7.5, 7.5 + i]}
                for i, u in enumerate(villagers)]
    server = FakeServer({u: {"Pos": (7.5, 64.0, 7.5 + i)} for i, u in enumerate(villagers)})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), carry=10, chop=0.25, start={}).setup()
    return server, g


def food(server):
    return sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Food aoe_res"))


def test_farms_are_free_ground_and_a_click_picks_them():
    _, g = farm_map()
    assert g.map.farms == dict.fromkeys(FARMS, gather.FARM_FOOD)
    assert all(g.map.free(x, z) for x in range(9, 12) for z in range(9, 12))      # the farmer stands on the farm
    assert g.map.spot((10, 10)) == {(x, z) for x in range(9, 12) for z in range(9, 12)}
    assert g.map.pick_tree((10.5, 65.62, 14.5), gather.direction(180, 30)) == (10, 10)
    assert g.map.pick_tree((10.5, 75, 14.5), gather.direction(180, 0)) is None


def test_one_farmer_per_farm():
    server, g = farm_map(("a", "b", "c"))
    g.selected = {"a", "b", "c"}
    g.send((10, 10))
    a, b, c = (g.villagers[u] for u in "abc")
    assert (a.tree, b.tree, c.tree) == ((10, 10), (16, 10), None)       # the next free farm, then nothing
    assert a.state == b.state == "to_tree" and c.state == "idle"
    assert g.farmers == {(10, 10): "a", (16, 10): "b"}
    assert 'data merge entity a {VillagerData:{profession:"minecraft:farmer"},Offers:{Recipes:[]}}' in server.log
    assert a.path[-1] in g.map.spot((10, 10))                            # it walks onto the farm
    g.selected = {"a"}
    g.send((16, 10))                                                     # taken: a goes back to its own farm
    assert a.tree == (10, 10) and g.farmers == {(10, 10): "a", (16, 10): "b"}


def test_a_farm_gets_empty_in_steps_and_turns_to_dirt():
    server, g = farm_map()
    g.select("v")
    g.send((10, 10))
    for _ in range(20000):
        g.step()
        if (10, 10) not in g.map.farms and g.villagers["v"].tree != (10, 10):   # an empty farm with no reseed (#3423)
            break
    v = g.villagers["v"]
    assert (10, 10) not in g.map.farms and v.tree != (10, 10) and (10, 10) not in g.farmers
    assert food(server) == g.stock["food"] == gather.FARM_FOOD and g.map.farms[(16, 10)] == gather.FARM_FOOD
    fills = [c for c in server.log if c.startswith("fill 9 63 9 11 64 11 ")]
    assert [c.split(" ", 7)[7] for c in fills] == [f"minecraft:wheat[age={a}] replace minecraft:wheat"
                                                  for a in (6, 5, 4, 3, 2, 1)] + \
        ["air replace minecraft:wheat", "minecraft:dirt replace minecraft:farmland"]
    mill = {(x, z) for x in range(12, 14) for z in range(14, 16)}
    cells = [(int(float(c.split()[2])), int(float(c.split()[4]))) for c in server.log if c.startswith("tp ")]
    assert any(max(abs(x - a), abs(z - b)) == 1 for x, z in cells for a, b in mill)    # the food goes to the mill


@pytest.mark.mc
def test_villager_farms_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=8.5)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.FARM.ID, x=11.5, y=11.5)
    src = str(tmp_path / "farm.aoe2scenario")
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
        farm, = g.map.farms
        x0, x1, z0, z1 = g.map.feet[farm]
        y = g.map.y((x0 + x1) // 2, (z0 + z1) // 2)

        def count(block, dy=0):                                        # blocks of a kind on the farm
            return sum("passed" in game.command(f"execute if block {x} {y + dy} {z} {block}")
                       for x in range(x0, x1) for z in range(z0, z1))
        assert count("minecraft:wheat") > 0 and count("minecraft:farmland", -1) > 0, "no crop on the farm"
        g.map.farms[farm] = 30                                         # a small farm: three loads
        g.select(uuid)
        g.send(farm)
        assert 'profession: "minecraft:farmer"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 90
        while g.map.farms.get(farm, 0) > 0 or g.villagers[uuid].state != "idle":
            assert time.time() < end, "the farm is not empty after 90 s"
            g.step()
        assert "has 30 " in game.command("scoreboard players get Food aoe_res")
        assert count("minecraft:wheat") == 0 and count("minecraft:farmland", -1) == 0, "crop is left"
        assert count("minecraft:dirt", -1) > 0, "no dirt"
