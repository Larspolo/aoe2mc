"""The plugin: an arrow that hits the minecart of a siege unit hurts its crew, and the minecart does not break (#3014).
A boat has this rule since #1386 (test_armenian_volley.py): the vanilla vehicle breaks after a few arrows."""
import shutil
import time

import pytest

from game import combat, run


@pytest.mark.mc
def test_an_archer_hurts_the_crew_of_a_scorpion_and_the_minecart_stays(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_fire_ship import health, uuid_of
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a floor in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone_bricks")
        game.command("team add red")
        game.command("team add blue")
        assert "Summoned" in summon(game, "ARCHER", 4.5, y, 10.5, "ar")
        assert "Summoned" in summon(game, "SCORPION", 20.5, y, 10.5, "sc")   # 16 blocks: in the range of an archer
        ar, sc = uuid_of(game, "ar"), uuid_of(game, "sc")
        assert "Stats: 1 units" in game.command(combat.stats_command(ar, "ARCHER"))
        assert "Stats: 1 units" in game.command(combat.stats_command(sc, "SCORPION"))     # the crew
        assert "Range: 1 units" in game.command(combat.range_command(ar, "ARCHER", 4))
        game.command("team join red @e[tag=ar]")
        game.command("team join blue @e[tag=sc]")
        game.command(f"execute as {sc} on passengers run team join blue @s")
        assert "Attack: 1 units" in game.command(f"aoe attack {ar} {sc}")
        start, hp = health(game, sc), []
        end = time.time() + 20
        while time.time() < end:
            time.sleep(0.5)
            hp.append(health(game, sc))
        assert "Test failed" not in game.command(f"execute if entity {sc}"), hp      # the minecart stays
        assert "Test failed" in game.command("execute if entity @e[type=item]")      # no minecart item on the floor
        assert min(hp) < start, (start, hp)                                           # the crew loses hit points
