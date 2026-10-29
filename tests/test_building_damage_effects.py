"""A hit on a building shows block particles and plays the hit sound; a building below half of its hit points burns
(#660, AoePlugin.java hitEffect and burn). The plugin uses the Bukkit API, not commands: a fake server sees nothing,
so the test runs on a real server and reads the burn tag and the log."""
import re
import shutil
import time

import pytest

from game import combat, run
from test_building_damage import hp


def tagged(game, uuid):
    return "Test passed" in game.command("execute if entity @e[type=slime,tag=aoe2mc.burning]")


def wait(cond, seconds=5):
    end = time.time() + seconds
    while time.time() < end and not cond():
        time.sleep(0.2)
    return cond()


@pytest.mark.mc
def test_hits_and_fire_of_a_building(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        game.command("team add p1")
        game.command("team add p2")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        game.command(f'summon husk 6.5 {y} 10.5 {{NoAI:1b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        assert game.command(combat.stats_command("@e[tag=a,limit=1]", "CHAMPION")).strip() == "Stats: 1 units"
        start = len(game.server.log)
        assert game.command(f"aoe attack @e[tag=a] {uuid}").strip() == "Attack: 1 units"
        full = combat.stats("HOUSE").hp
        assert wait(lambda: hp(game, uuid) <= full - 3 * combat.damage("CHAMPION", "HOUSE"), 30)   # 3 hits, each with the hit effect
        game.command("kill @e[tag=a]")
        assert not wait(lambda: tagged(game, uuid), 2)                 # above half: no fire
        game.command(f"scoreboard players set {uuid} aoe_hp {full // 5}")
        assert wait(lambda: tagged(game, uuid))                        # below half: it burns
        game.command(f"scoreboard players set {uuid} aoe_hp {full}")   # repaired
        assert wait(lambda: not tagged(game, uuid))
        game.command(f"scoreboard players set {uuid} aoe_hp 10")
        assert wait(lambda: tagged(game, uuid))
        game.command(f'summon husk 6.5 {y} 10.5 {{NoAI:1b,Tags:["b"]}}')
        game.command("team join p1 @e[tag=b]")
        game.command(combat.stats_command("@e[tag=b,limit=1]", "CHAMPION"))
        game.command(f"aoe attack @e[tag=b] {uuid}")
        assert wait(lambda: hp(game, uuid) is None, 10)                # destroyed: the target is gone
        assert "Test failed" in game.command(f"execute if entity {uuid}")
        time.sleep(1.5)                                                # one burn cycle without the building
        errors = [ln for ln in game.server.log[start:] if re.search(r"Exception|/ERROR\]|Could not pass event", ln)]
        assert not errors, errors
