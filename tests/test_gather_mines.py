"""game/gather.py: villagers mine gold and stone (#390). The fast tests use the fake server of test_gather."""
import json
import math
import os
import re
import shutil
import time

import pytest
from test_gather import FakeServer

from game import gather, run


def mine_world(tiny_world, extra=()):
    """The tiny world data (one gold mine) with the villager on its column, and a Gather with small numbers."""
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        data = json.load(f)
    data["objects"] += list(extra)
    m = gather.Map(data)
    vil, = [o for o in data["objects"] if o["kind"] == "unit" and "VILLAGER" in o["name"]]
    x, z = int(vil["tile"][0] * 4), int(vil["tile"][1] * 4)
    server = FakeServer({vil["uuid"]: {"Pos": (x + 0.5, m.y(x, z), z + 0.5)}})
    return vil["uuid"], server, gather.Gather(server, data, tick=0.25, carry=3, chop=0.25).setup()


def test_the_map_knows_the_mines(tiny_world):
    uuid, server, g = mine_world(tiny_world)
    (tile, gold), = g.map.mines.items()
    assert gold == 800 and g.map.res[tile] == "gold" and tile in g.map.feet
    assert g.map.amount(tile) == 800 and tile not in g.map.trees
    T = g.map.T
    px, pz = tile[0] * T + T / 2, tile[1] * T + T + 4                  # 4 blocks south of the mine, look north
    eye = (px, g.map.y(int(px), int(pz)) + 1.62, pz)
    assert g.map.pick_tree(eye, gather.direction(180, 10)) == tile


def test_a_miner_carries_gold_to_the_town_center(tiny_world):
    uuid, server, g = mine_world(tiny_world)
    tile, = g.map.mines
    g.select(uuid)
    g.send(tile)
    assert f'data merge entity {uuid} {{VillagerData:{{profession:"minecraft:toolsmith"}}}}' in server.log
    for _ in range(300):
        g.step()
    gold = sum(int(c.split()[-1]) for c in server.log if c.startswith("scoreboard players add Gold aoe_res"))
    assert gold >= 6 and g.stock["gold"] == gold and g.wood == 0                     # two loads or more
    assert g.map.mines[tile] == 800 - gold - g.villagers[uuid].load


def test_an_empty_mine_goes_away_and_the_miner_goes_to_the_next(tiny_world):
    uuid, server, g = mine_world(tiny_world)
    first, = g.map.mines
    nx, nz = first[0] - 3, first[1]                                      # a second gold mine 3 tiles west
    g.map.mines[(nx, nz)], g.map.res[(nx, nz)], g.map.names[(nx, nz)] = 50, "gold", "GOLD_MINE"
    g.map.blocked |= g.map.cells((nx, nz))
    g.map.mines[first] = 3
    g.select(uuid)
    g.send(first)
    for _ in range(300):
        g.step()
        if g.villagers[uuid].tree != first:
            break
    fills = [c for c in server.log if c.startswith("fill ")]
    assert any(c.endswith("air replace minecraft:gold_ore") for c in fills)
    assert any(c.endswith("air replace minecraft:barrier") for c in fills)
    assert g.map.mines[first] == 0 and g.villagers[uuid].tree == (nx, nz) and g.villagers[uuid].state == "to_tree"
    g.map.mines[(nx, nz)] = 0
    g.villagers[uuid].path = []
    g.step()
    assert g.villagers[uuid].state == "idle"                             # no gold mine left: stop


@pytest.mark.mc
def test_villager_mines_gold_on_a_server(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(world / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(world) as game:
        game.forceload()
        end = time.time() + 60                                         # entities load in other threads
        while True:
            g = gather.Gather(game, data, tick=0.05, carry=3, chop=0.05).setup()
            if g.villagers:
                break
            assert time.time() < end, "the villager did not load"
            time.sleep(1)
        uuid, = g.villagers
        tile, = g.map.mines
        g.map.mines[tile] = 6                                            # two loads, then the mine is empty
        g.select(uuid)
        g.send(tile)
        assert 'profession: "minecraft:toolsmith"' in game.command(f"data get entity {uuid} VillagerData")
        end = time.time() + 90
        while g.map.mines[tile] or g.villagers[uuid].state != "idle":
            assert time.time() < end, "the mine is not empty after 90 s"
            g.step()
        assert re.search(r"has 6\b", game.command("scoreboard players get Gold aoe_res"))
        (fx0, fx1, fz0, fz1), ys, _, _ = g.site(tile)
        for x in range(fx0, fx1):
            for z in range(fz0, fz1):
                for y in range(min(ys), max(ys) + 4):
                    assert "passed" in game.command(f"execute if block {x} {y} {z} minecraft:air"), (x, y, z)
        assert math.isfinite(g.pos(uuid)[0])
