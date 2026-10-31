"""game/gather.py: villagers mine gold and stone (#390). The fast tests use a fake server; the mc test a real one."""
import contextlib
import io
import json
import math
import time

import pytest
from test_gather import FakeServer, grid

from game import gather, run


def mine_map(camp=True):
    """A flat 24 × 24 map (tile size 1): a town center and a mining camp of player 1, a villager, two gold mines
    (one at x.0: 2 × 2 tiles) and a stone mine."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]},
               {"kind": "other", "name": "GOLD_MINE", "tile": [12.5, 12.5]},
               {"kind": "other", "name": "GOLD_MINE", "tile": [17.0, 12.0]},
               {"kind": "other", "name": "STONE_MINE", "tile": [12.5, 18.5]}]
    if camp:
        objects.append({"kind": "building", "name": "MINING_CAMP", "player": 1, "footprint": [12, 14, 14, 16]})
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    return server, gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), carry=10, chop=0.25, start={}).setup()


def score(server, name):
    return sum(int(c.split()[-1]) for c in server.log if c.startswith(f"scoreboard players add {name} aoe_res"))


def mine(g, steps=20000, until=lambda: False):
    for _ in range(steps):
        g.step()
        if until():
            break


def test_mines_and_their_footprints():
    _, g = mine_map()
    gold, stone = (gather.MINES[n][1] for n in ("GOLD_MINE", "STONE_MINE"))
    assert g.map.mines == {"gold": {(12, 12): gold, (17, 12): gold}, "stone": {(12, 18): stone}}
    assert g.map.spot((12, 12)) == {(12, 12)}
    assert g.map.spot((17, 12)) == {(16, 11), (17, 11), (16, 12), (17, 12)}      # at x.0: 2 × 2 tiles
    assert not any(g.map.free(*c) for c in g.map.spot((17, 12)))
    assert g.map.resource((12, 18)) == "stone" and g.map.resource((17, 12)) == "gold"
    eye = (16.5, 65.62, 16.5)
    assert g.map.pick_tree(eye, gather.direction(180, 20)) == (17, 12)    # look north and down at the big mine
    assert g.map.pick_tree((16.5, 75, 16.5), gather.direction(180, 0)) is None


def test_a_click_on_a_mine_sends_a_miner_and_the_load_goes_to_the_camp():
    server, g = mine_map()
    g.select("v")
    g.send((12, 12))
    v = g.villagers["v"]
    assert v.state == "to_tree" and v.res == "gold" and v.tree == (12, 12)
    assert 'data merge entity v {VillagerData:{profession:"minecraft:toolsmith"},Offers:{Recipes:[]}}' in server.log
    mine(g, until=lambda: g.stock["gold"] >= 30)
    assert g.stock["gold"] == score(server, "Gold") == 30
    assert g.map.mines["gold"][(12, 12)] <= gather.MINES["GOLD_MINE"][1] - 30
    camp = set().union(*g.map.drops["gold"])
    assert len(g.map.drops["gold"]) == 2 and (12, 14) in camp
    cells = [(math.floor(float(c.split()[2])), math.floor(float(c.split()[4]))) for c in server.log if c.startswith("tp ")]
    tc = {(x, z) for x in range(2, 5) for z in range(2, 5)}
    assert not any(max(abs(x - a), abs(z - b)) == 1 for x, z in cells for a, b in tc)   # the camp is nearer
    g.send((12, 18))
    assert 'data merge entity v {VillagerData:{profession:"minecraft:mason"},Offers:{Recipes:[]}}' in server.log and v.res == "stone"


def test_an_empty_mine_goes_away_and_the_miner_goes_to_the_next_one():
    server, g = mine_map()
    g.map.mines["gold"][(12, 12)] = 20
    g.select("v")
    g.send((12, 12))
    mine(g, until=lambda: g.villagers["v"].tree == (17, 12))
    v = g.villagers["v"]
    assert g.map.mines["gold"][(12, 12)] == 0 and v.tree == (17, 12) and v.state == "to_tree"
    assert g.stock["gold"] == 20 and g.map.free(12, 12) and (12, 12) not in g.map.mine_at
    fills = [c for c in server.log if c.startswith("fill 12 64 12 12 68 12 air replace")]
    assert [c.split()[-1] for c in fills] == ["minecraft:" + b for b in gather.MINE_BLOCKS["gold"] + ("barrier",)]
    assert g.map.mines["stone"][(12, 18)] == gather.MINES["STONE_MINE"][1]   # not a mine of the other kind


def test_a_miner_stops_when_no_mine_of_the_kind_is_left():
    server, g = mine_map(camp=False)
    g.map.mines["stone"][(12, 18)] = 10
    g.select("v")
    g.send((12, 18))
    mine(g, until=lambda: g.stock["stone"] and g.villagers["v"].state == "idle")
    assert g.villagers["v"].state == "idle" and g.stock["stone"] == score(server, "Stone") == 10


@pytest.mark.mc
def test_villager_mines_gold_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.other import OtherInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(16)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.TOWN_CENTER.ID, x=4, y=4)
    um.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=8.5, y=8.5)
    um.add_unit(scenarios.PlayerId.GAIA, OtherInfo.GOLD_MINE.ID, x=10.5, y=10.5)
    src = str(tmp_path / "gold.aoe2scenario")
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
        tile, = g.map.mines["gold"]
        spot = g.map.spot(tile)
        (x0, z0), (x1, z1) = min(spot), max(spot)
        y = min(g.map.y(*c) for c in g.map.around(spot))

        def heap():                                                    # blocks of the heap in the footprint
            return sum("passed" in game.command(f"execute if block {x} {y + dy} {z} minecraft:{b}")
                       for x in range(x0, x1 + 1) for z in range(z0, z1 + 1) for dy in range(3)
                       for b in gather.MINE_BLOCKS["gold"])
        assert heap() > 0, "the converter made no heap"
        g.map.mines["gold"][tile] = 30                                 # a small mine: three loads
        g.select(uuid)
        g.send(tile)
        assert 'profession: "minecraft:toolsmith"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 90
        while g.map.mines["gold"][tile] > 0 or g.villagers[uuid].state != "idle":
            assert time.time() < end, "the mine is not empty after 90 s"
            g.step()
        assert "has 30 " in game.command("scoreboard players get Gold aoe_res")
        assert heap() == 0, "the heap is still there"
