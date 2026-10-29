"""Ranged units and clicks attack an enemy building in the game program (#608): AoePlugin.java and game/gather.py."""
import math
import shutil
import time

import pytest

from game import combat, gather, run

from test_building_damage import hp
from test_gather import FakeServer, grid


def setup():
    objects = [{"kind": "unit", "name": "ARCHER", "player": 1, "uuid": "s-1", "tile": [2.5, 10.5]},
               {"kind": "building", "name": "HOUSE", "player": 2, "footprint": [8, 8, 12, 12], "tile": [10, 10]},
               {"kind": "building", "name": "HOUSE", "player": 1, "footprint": [8, 14, 12, 18], "tile": [10, 16]}]
    server = FakeServer({"s-1": {"Pos": (2.5, 64.0, 10.5)}, "Steve": {}})
    g = gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects)).setup()
    return server, g


def click(server, g, at, look):
    """Steve stands at block `at` and looks at the point `look` (x, y, z)."""
    eye = (at[0], 64.0, at[1])
    dx, dy, dz = look[0] - eye[0], look[1] - eye[1] - 1.62, look[2] - eye[2]
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": eye, "Rotation": (yaw, pitch)}
    server.log.clear()
    g.click("Steve")
    return server.log


def test_click_on_an_enemy_building_sends_the_selected_soldiers_to_attack():
    server, g = setup()
    g.select("s-1")
    uuid = combat.target_uuid([8, 8, 12, 12])
    assert set(g.forts) == {uuid}                                      # the own house is no target
    log = click(server, g, (4.5, 10.5), (8.5, 65.0, 10.5))
    assert [c for c in log if c.startswith("aoe attack")] == [f"aoe attack @e[tag={gather.SELECT}] {uuid}"]
    assert click(server, g, (4.5, 16.5), (8.5, 65.0, 16.5)) and not \
        [c for c in server.log if c.startswith("aoe attack")]          # an own building: no attack
    g.selected = set()
    assert not [c for c in click(server, g, (4.5, 10.5), (8.5, 65.0, 10.5)) if c.startswith("aoe attack")]


def test_paths_go_through_the_footprint_after_the_fall():
    server, g = setup()
    g.select("s-1")
    click(server, g, (4.5, 10.5), (8.5, 65.0, 10.5))
    assert (10, 10) in g.map.blocked
    server.command = lambda cmd, c=server.command: "Test passed" if cmd.startswith("execute if entity ") else c(cmd)
    g.step()
    assert (10, 10) in g.map.blocked                                   # it stands
    server.command = lambda cmd, c=server.command: "Test failed" if cmd.startswith("execute if entity ") else c(cmd)
    g.step()
    assert not {(x, z) for x in range(8, 12) for z in range(8, 12)} & g.map.blocked and not g.forts
    assert (10, 10) in g.map.path((2, 10), {(18, 10)})                 # the straight way through the footprint
    assert (10, 16) in g.map.blocked                                   # the own house stays


@pytest.mark.mc
def test_an_archer_shoots_a_house(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        game.command(f'summon skeleton 1.5 {y} 10.5 {{NoAI:1b,Tags:["a"],'      # 6.5 blocks from the wall
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command("team join p1 @e[tag=a]")
        assert game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command("@e[tag=a,limit=1]", "ARCHER", 4)).strip() == "Range: 1 units"
        assert game.command(f"aoe attack @e[tag=a] {uuid}").strip() == "Attack: 1 units"
        seen, end = [combat.BUILDINGS["HOUSE"].hp], time.time() + 20
        while time.time() < end:
            if (h := hp(game, uuid)) != seen[-1]:
                seen.append(h)
            time.sleep(0.1)
        assert len(seen) >= 6 and all(a - b == 1 for a, b in zip(seen, seen[1:])), seen   # 1 per shot
