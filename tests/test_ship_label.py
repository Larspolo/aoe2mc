"""The plugin: `aoe label` of a ship names its crew, the first passenger of the boat, as of a siege unit (#3086).
`train.research()` sends it with the boat UUID after Medium Warships (Galley to War Galley)."""
import re
import shutil

import pytest

from game import run


@pytest.mark.mc
def test_the_label_of_a_galley_goes_to_its_crew_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 21 {y} 21 water")
        assert "Summoned" in summon(game, "GALLEY", 10.5, y + 0.5, 10.5, "g")
        ints = [int(i) for i in re.findall(r"-?\d+", game.command(
            "data get entity @e[type=oak_boat,tag=g,limit=1] UUID").rsplit(":", 1)[-1])]
        h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
        boat = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
        game.command(f"execute as {boat} on passengers run data merge entity @s "
                     "{CustomName:{text:\"Galley\",color:\"blue\"}}")
        assert "Label: 1 units" in game.command(f"aoe label {boat} War Galley")
        name = game.command(f"data get entity {boat} Passengers[0].CustomName")
        assert "War Galley" in name and "blue" in name, name           # the player color stays
