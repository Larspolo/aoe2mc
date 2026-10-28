"""A ship keeps the stance that the player gives it (#3018): a galley with "No Attack" does not shoot an enemy ship in
its sight. The stance is kept under the UUID of the boat, as the stance menu sends it."""
import re
import shutil
import time

import pytest

from game import combat, run


@pytest.mark.mc
def test_a_galley_with_no_attack_does_not_shoot_an_enemy_ship_on_a_server(tiny_world, tmp_path):
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
        ids = {}
        for tag, x in (("a", 4.5), ("bb", 16.5)):                        # own UUIDs: tags of other lengths
            assert "Summoned" in summon(game, "GALLEY", x, y + 0.5, 10.5, tag)
            ints = [int(i) for i in re.findall(r"-?\d+", game.command(
                f"data get entity @e[type=oak_boat,tag={tag},limit=1] UUID").rsplit(":", 1)[-1])]
            h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
            ids[tag] = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], "GALLEY"))
            assert "Range: 1 units" in game.command(combat.range_command(ids[tag], "GALLEY", 4, rate=20))
        game.command("team add red")
        game.command("team add blue")
        game.command("team join red @e[tag=a]")
        game.command("team join blue @e[tag=bb]")
        game.command(f"execute as {ids['a']} on passengers run team join red @s")
        game.command(f"execute as {ids['bb']} on passengers run team join blue @s")
        assert game.command(f"aoe stance {ids['a']} no_attack").strip() == "Stance: 1 units"
        assert game.command(f"aoe stance {ids['a']}").strip() == "Stance: no_attack"
        hp = []
        for _ in range(12):                                             # 6 seconds: the crew of bb keeps its hit points
            time.sleep(0.5)
            out = game.command(f"execute as {ids['bb']} on passengers run data get entity @s Health")
            hp.append(float(m[0]) if (m := re.findall(r"(\d+\.?\d*)f", out)) else 0.0)
        assert len(set(hp)) == 1 and hp[0] > 0, hp
