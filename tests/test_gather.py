"""game/gather.py: villagers gather wood (#138). The fast tests use a fake server; the mc test a real one."""
import json
import math
import os
import re
import shutil
import time

import pytest

import units
from game import gather, run


def grid(rows, objects=()):
    """aoe2mc.json data from rows of ground heights ("-" = water) with tile size 1."""
    return {"tile_size": 1, "ground": [" ".join(map(str, r)) for r in rows], "objects": list(objects)}


def test_path_goes_around_water_buildings_and_cliffs():
    rows = [[64] * 10 for _ in range(10)]
    for z in range(8):
        rows[z][5] = "-"                                               # a river with a ford at z = 8 and 9
    rows[9][5] = 70                                                    # a cliff: only z = 8 is low
    m = gather.Map(grid(rows, [{"kind": "building", "name": "HOUSE", "player": 1, "footprint": [2, 7, 4, 10]}]))
    path = m.path((1, 1), {(8, 1)})
    assert path[-1] == (8, 1) and (5, 8) in path
    assert all(m.free(*c) for c in path) and not {(2, 8), (3, 8)} & set(path)
    assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1 for a, b in zip([(1, 1)] + path, path))
    rows[8][5] = "-"
    assert gather.Map(grid(rows)).path((1, 1), {(8, 1)}) is None


def test_pick_unit_and_tree():
    m = gather.Map(grid([[64] * 20 for _ in range(20)], [{"kind": "other", "name": "TREE_OAK", "tile": [10.5, 4.5]}]))
    eye = (10.5, 65.62, 15.5)
    assert m.pick_tree(eye, gather.direction(180, 5)) == (10, 4)        # look north, a little down
    assert m.pick_tree(eye, gather.direction(0, 10)) is None            # south: no tree
    assert m.pick_tree(eye, gather.direction(180, 60)) is None          # the ray hits the ground first
    units = {"a": (10.5, 64.0, 12.5), "b": (12.5, 64.0, 12.5)}
    d = gather.direction(180, math.degrees(math.atan2(0.62, 3)))
    assert gather.pick_unit(eye, d, units) == "a" and gather.pick_unit(eye, gather.direction(90, 0), units) is None


class FakeServer:
    """Answers the commands of Gather like a server; one player "Steve" can click."""

    def __init__(self, entities):
        self.entities, self.log, self.scores = entities, [], {}

    def command(self, cmd):
        self.log.append(cmd)
        if m := re.fullmatch(r"data get entity (\S+) (Pos|Rotation)", cmd):
            if m[1] not in self.entities:
                return "No entity was found"
            v = self.entities[m[1]][m[2]]
            return f"{m[1]} has the following entity data: [{', '.join(f'{x}d' for x in v)}]"
        if (m := re.match(r"summon \S+ (\S+) (\S+) (\S+) .*?UUID:\[I;(-?\d+),(-?\d+),(-?\d+),(-?\d+)\]", cmd)) \
                and (u := units.uuid_str([int(a) for a in m.groups()[3:]])) not in self.entities:
            self.entities[u] = {"Pos": tuple(map(float, m.groups()[:3]))}    # a summoned unit lives (#3122)
        if m := re.fullmatch(r"tp (\S+) (\S+) (\S+) (\S+) .*", cmd):
            self.entities[m[1]]["Pos"] = tuple(map(float, m.groups()[1:]))
        if m := re.fullmatch(r"execute if entity @a\[scores=\{(\w+)=1\.\.\}\]", cmd):
            return "Test passed, count: 1" if self.scores.get(m[1]) else "Test failed"
        if cmd == "list":
            return "There are 1 of a max of 20 players online: Steve"
        if m := re.fullmatch(r"scoreboard players get Steve (\w+)", cmd):
            return f"Steve has {self.scores.get(m[1], 0)} [{m[1]}]"
        if m := re.fullmatch(r"scoreboard players reset Steve (\w+)", cmd):
            self.scores.pop(m[1], None)
        return ""

    def wood(self):
        return sum(int(c.split()[-1]) for c in self.log if c.startswith("scoreboard players add Wood aoe_res"))


def tiny(tiny_world):
    with open(os.path.join(tiny_world[0], "aoe2mc.json")) as f:
        data = json.load(f)
    m = gather.Map(data)
    vil, = [o for o in data["objects"] if o["kind"] == "unit" and "VILLAGER" in o["name"]]
    x, z = int(vil["tile"][0] * 4), int(vil["tile"][1] * 4)
    server = FakeServer({vil["uuid"]: {"Pos": (x + 0.5, m.y(x, z), z + 0.5)}})
    return data, vil["uuid"], server, gather.Gather(server, data, tick=0.25, carry=3, chop=0.25, start={}).setup()


def test_villager_carries_wood_to_the_town_center(tiny_world):
    data, uuid, server, g = tiny(tiny_world)
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    for _ in range(400):
        g.step()
    assert server.wood() >= 6                                          # at least two trips of 3 wood
    cells = [(math.floor(float(c.split()[2])), math.floor(float(c.split()[4]))) for c in server.log if c.startswith("tp ")]
    assert cells and all(g.map.free(*c) for c in cells)
    tc = set().union(*g.map.drops["wood"])
    assert any(max(abs(x - a), abs(z - b)) == 1 for x, z in cells for a, b in tc)    # next to the town center
    assert g.map.trees[tree] == gather.TREE_WOOD - server.wood() - g.villagers[uuid].load


def test_clicks_select_a_villager_and_send_it_to_a_tree(tiny_world):
    data, uuid, server, g = tiny(tiny_world)
    vx, vy, vz = server.entities[uuid]["Pos"]
    server.entities["Steve"] = {"Pos": (vx, vy, vz - 3), "Rotation": (0.0, math.degrees(math.atan2(0.62, 3)))}
    server.scores["aoe_talk"] = 1                                      # a right click on the villager
    for name in g.clicks():
        g.click(name)
    assert g.selected == {uuid} and f"data merge entity {uuid} {{Glowing:1b}}" in server.log
    assert not server.scores
    (tx, ty), = g.map.trees
    T = g.map.T
    px, pz = tx * T + T / 2, ty * T + T + 4                            # 4 blocks south of the tree, look north
    y = g.map.y(int(px), int(pz))
    server.entities["Steve"] = {"Pos": (px, y, pz), "Rotation": (180.0, 10.0)}
    server.scores["aoe_use"] = 1
    for name in g.clicks():
        g.click(name)
    assert g.villagers[uuid].state == "to_tree" and g.villagers[uuid].tree == (tx, ty)


def test_a_villager_that_chops_wood_looks_like_a_lumberjack(tiny_world):
    data, uuid, server, g = tiny(tiny_world)
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    g.send(tree)                                                       # the second order sends no command
    look = gather.profession(uuid, "fletcher")
    assert server.log.count(look) == 1


def test_event_log_gives_the_configured_timing(tiny_world):
    import io

    import measure_gather
    data, uuid, server, _ = tiny(tiny_world)
    now, log = [0.0], io.StringIO()
    g = gather.Gather(server, data, tick=0.25, carry=3, chop=0.5, log=log, clock=lambda: now[0], start={}).setup()
    tree, = g.map.trees
    g.select(uuid)
    g.send(tree)
    for _ in range(400):
        g.step()
        now[0] += 0.25
    events = [json.loads(line) for line in log.getvalue().splitlines()]
    assert [e["event"] for e in events[:5]] == ["walk", "chop", "carry", "drop", "walk"]
    assert all(e["villager"] == uuid and len(e["pos"]) == 3 for e in events)
    drops = [e for e in events if e["event"] == "drop"]
    assert [e["wood"] for e in drops[:3]] == [3, 6, 9] and g.wood == server.wood()
    m = measure_gather.analyze(events)
    assert m["chop"] == pytest.approx(2.0) and m["trip"] > 0
    assert 3.0 < m["walk"] <= 4 * 1.42                                 # 1 block per tick, diagonal steps 1.41
    conf = measure_gather.configured(0.25, 0.5, 3, m["trip_blocks"])
    assert "| Chop (wood/s) | 2.00 | 2.00 | 0.39 | 0.66 |" in measure_gather.table(m, conf, 4)


def test_fell_removes_the_tree_and_its_barriers_and_leaves_a_flat_stump():
    m = grid([], [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 6.5]}])
    m["tile_size"] = 4
    # the ground of the converter is on top of the barriers in the footprint (x 20..23, z 24..27)
    m["ground"] = [" ".join("67" if 20 <= x < 24 and 24 <= z < 28 else "64" for x in range(48)) for z in range(48)]
    server = FakeServer({})
    g = gather.Gather(server, m, start={})
    g.fell((5, 6))
    fills = [c for c in server.log if c.startswith("fill ")]
    assert "fill 20 62 24 23 67 27 air replace minecraft:barrier" in fills                # the footprint only
    assert any(c.endswith("air replace #minecraft:logs") for c in fills)
    assert any(c.endswith("air replace #minecraft:leaves") for c in fills)
    assert server.log[-1] == "setblock 22 63 26 minecraft:spruce_log[axis=y]"          # in the ground, after the fills


def test_a_cut_tree_lies_on_the_ground_and_gets_shorter():
    """From the first chop a trunk lies next to the stump: one log less per 25 wood, only the stump at 0 (#308)."""
    m = grid([], [{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 6.5]}])
    m["tile_size"] = 4
    m["ground"] = [" ".join("67" if 20 <= x < 24 and 24 <= z < 28 else "64" for x in range(48)) for z in range(48)]
    server = FakeServer({})
    g = gather.Gather(server, m, start={})
    tile = (5, 6)

    def level(wood):
        server.log.clear()
        g.map.trees[tile] = wood
        g.trunk(tile) if wood else g.fell(tile)
        return [c for c in server.log if "oak_log[axis=x]" in c and c.endswith("barrier")]

    assert level(99) == ["fill 20 64 25 23 64 25 minecraft:oak_log[axis=x] replace minecraft:barrier"]
    assert "setblock 22 63 26 minecraft:spruce_log[axis=y]" in server.log                  # the stump
    assert any(c.endswith("air replace #minecraft:logs") for c in server.log)            # the standing tree goes
    assert "fill 20 65 25 20 65 25 minecraft:oak_leaves[persistent=true] keep" in server.log   # the crown on the tip
    assert level(76) == [] and server.log == []                                          # no change: no command
    for wood, x in ((75, 21), (50, 22), (26, None), (25, 23)):
        assert level(wood) == ([f"fill {x} 64 25 23 64 25 minecraft:oak_log[axis=x] replace minecraft:barrier"]
                               if x else []), wood
        assert not x or "fill 20 64 25 23 65 25 minecraft:barrier replace minecraft:oak_log" in server.log
    assert level(0) == [] and "fill 20 64 25 23 65 25 air replace minecraft:oak_log" in server.log
    assert server.log[-1] == "setblock 22 63 26 minecraft:spruce_log[axis=y]"


@pytest.mark.mc
def test_measured_gather_timing_is_near_the_configured_timing():
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import measure_gather
    events, T = measure_gather.measure(distance=10, loads=2)
    m = measure_gather.analyze(events)
    assert m["trip_blocks"] is not None, f"no full trip (2 drops) in the log: {[e['event'] for e in events][-20:]}"
    conf = measure_gather.configured(0.25, measure_gather.WORK_SECONDS["wood"], 10, m["trip_blocks"],
                                     measure_gather.ai.walk_speed("VILLAGER", T))       # Paper (#437)
    print(measure_gather.table(m, conf, T))
    for k in ("walk", "chop", "trip"):
        assert m[k] == pytest.approx(conf[k], rel=0.1), (k, m[k], conf[k])


@pytest.mark.mc
def test_villager_gathers_wood_on_a_server(tiny_world, tmp_path):
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
            g = gather.Gather(game, data, tick=0.05, carry=3, chop=0.05, start={}).setup()
            if g.villagers:
                break
            assert time.time() < end, "the villager did not load"
            time.sleep(1)
        uuid, = g.villagers
        tree, = g.map.trees
        g.select(uuid)
        g.send(tree)
        look = game.command(f"data get entity {uuid} VillagerData")              # the merge keeps the level
        assert 'profession: "minecraft:fletcher"' in look and "level: 2" in look, look
        end = time.time() + 60
        while "has 0 " in game.command("scoreboard players get Wood aoe_res"):
            assert time.time() < end, "no wood after 60 s"
            g.step()
        assert re.search(r"has [1-9]", game.command("scoreboard players get Wood aoe_res"))
        x, y, z = g.pos(uuid)
        assert (math.floor(x), math.floor(z)) == g.villagers[uuid].cell and y == g.map.y(*g.villagers[uuid].cell)
