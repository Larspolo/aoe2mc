"""game/map_table.py: the framed minimap logs no "Block-attached entity at invalid position" (#3262). The summon
command reads the tag before it moves the entity to its position: a tag without Pos puts the frame at 0 0 0 during
the load, more than 16 blocks from its block_pos, and Minecraft logs the error."""
import os
import re
import shutil

import pytest
from test_minimap_click import setup as table_setup

from game import run


def summon(server):
    return next(c for c in server.log if "summon minecraft:glow_item_frame" in c)


def test_the_frame_tag_has_the_pos_of_its_block():
    server, g = table_setup()
    pos = [float(v) for v in re.search(r"Pos:\[([^\]]*)\]", summon(server))[1].replace("d", "").split(",")]
    block = [int(v) for v in re.search(r"block_pos:\[I;([^\]]*)\]", summon(server))[1].split(",")]
    assert pos == [12.5, 65.0, 12.5] and block == [12, 65, 12]


@pytest.mark.mc
def test_a_summoned_frame_logs_no_invalid_position(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not available")
    server, g = table_setup()
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.command("forceload add 0 0 31 31")
        for c in server.log:
            if c.startswith(("setblock", "summon")):
                game.command(c)
        assert "passed" in game.command("execute if entity @e[type=glow_item_frame,tag=aoe2mc.map_table]")
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            text = f.read()
    assert "Block-attached entity at invalid position" not in text, text[-2000:]
