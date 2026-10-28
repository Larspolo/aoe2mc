"""Live replay: the crew of a ship or a siege unit leaves a death mark too (#3019, Deaths.java of the plugin). Fake
RCON and a real Paper server."""
import os
import re
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402

MARKS = "execute if entity @e[type=text_display,tag=aoe2mc.deathmark]"


def marks(game):
    found = re.search(r"Count: (\d+)", game.command(MARKS))
    return int(found.group(1)) if found else 0


def crew(game, i, vehicle, tag):
    """A unit with the AoE2 values in team aoe_p1, mounted on the vehicle with the UUID ending in hex i."""
    game.command(f'summon minecraft:pillager 8 80 8 {{UUID:[I;0,0,0,{i}],NoAI:1b,Tags:["{tag}"]}}')
    game.command(f"team join aoe_p1 00000000-0000-0000-0000-0000000000{i:02x}")
    game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 infantry - 20")
    game.command(f"ride 00000000-0000-0000-0000-0000000000{i:02x} mount 00000000-0000-0000-0000-0000000000{vehicle:02x}")


@pytest.mark.mc
def test_the_crew_of_a_tagged_vehicle_leaves_a_mark(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        game.command("team add aoe_p1")
        game.command("team modify aoe_p1 color red")
        assert "Death marks: on" in game.command("aoe deathmarks on")
        # a boat with no tag: its crew makes no mark
        game.command("summon minecraft:oak_boat 8 80 8 {UUID:[I;0,0,0,181]}")
        crew(game, 182, 181, "c1")
        game.command("kill 00000000-0000-0000-0000-0000000000b6")
        assert marks(game) == 0
        # a boat with the tag: its crew makes one mark in the team color, at the place of the boat
        game.command(f'summon minecraft:oak_boat 8 80 8 {{UUID:[I;0,0,0,177],Tags:["{replay.COUNTED}"]}}')
        crew(game, 178, 177, "c2")
        game.command("kill 00000000-0000-0000-0000-0000000000b2")
        assert marks(game) == 1
        text = game.command("data get entity @e[type=text_display,tag=aoe2mc.deathmark,limit=1] text")
        assert "☠" in text and "red" in text
        time.sleep(6)
        assert marks(game) == 0
        # a minecart with the tag: its crew makes one mark too
        game.command(f'summon minecraft:minecart 8 80 8 {{UUID:[I;0,0,0,179],Tags:["{replay.COUNTED}"]}}')
        crew(game, 180, 179, "c3")
        game.command("kill 00000000-0000-0000-0000-0000000000b4")
        assert marks(game) == 1
        time.sleep(6)
