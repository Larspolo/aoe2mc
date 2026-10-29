"""The shots of a Spanish Cannon Galleon lead a moving target (#2430, AoE2 DE wiki "Cannon Galleon": "their projectiles
are much faster (7 tiles/second instead of 3 tiles/s) and hit moving targets with Ballistics-like behavior"): the key
"lead", train.lead_command and the tag aoe2mc.lead of the plugin. The arrows of the plugin fly at 3 blocks per tick for
each unit, faster than 7 tiles/s at Normal speed: the faster projectile needs no change. Fake server, and a server."""
import re
import shutil
import time

import pytest
from test_armenian_volley import summoned
from test_dock_train import dock_map

from game import civs, combat, run, train


def test_a_unit_of_the_key_lead_leads_its_target():
    names = civs.value("lead", "SPANISH", ())
    assert names
    for name in names:
        uuid, log = summoned("SPANISH", name)
        assert f"tag {uuid} add aoe2mc.lead" in log, name


def test_only_the_units_of_the_key_lead_lead():
    for civ, name in (("SPANISH", "GALLEON"), ("TURKS", "CANNON_GALLEON")):
        uuid, log = summoned(civ, name)
        assert any("aoe2mc.lead" in c for c in log) == (name in civs.value("lead", civ, ())), (civ, name)


def test_the_elite_upgrade_keeps_the_lead():
    server, g = dock_map()
    g.data["players"]["1"]["civ"] = "SPANISH"
    g.soldiers["s"] = "CANNON_GALLEON"
    del server.log[:]
    train.research(g, {"name": "ELITE_CANNON_GALLEON_UPGRADE", "player": "Steve"})
    assert g.soldiers["s"] == "ELITE_CANNON_GALLEON" and "tag s add aoe2mc.lead" in server.log


@pytest.mark.mc
def test_a_tagged_cannon_galleon_hits_a_walking_unit_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool and a road in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 62 50")
        game.command(f"fill 0 {y - 1} 0 60 {y} 48 stone_bricks")
        game.command(f"fill 2 {y} 20 8 {y} 28 water")
        assert "Summoned" in summon(game, "CANNON_GALLEON", 5.5, y + 0.5, 24.5, "s")
        ints = [int(i) for i in re.findall(r"-?\d+", game.command(
            "data get entity @e[tag=s,limit=1] UUID").rsplit(":", 1)[-1])]
        h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
        ship = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
        assert "Stats: 1 units" in game.command(combat.stats_command(ship, "CANNON_GALLEON"))
        assert "Range: 1 units" in game.command(combat.range_command(ship, "CANNON_GALLEON", 4))
        game.command(f"tag {ship} add aoe2mc.lead")
        game.command(f'summon zombie 55.5 {y + 1} 2.5 {{IsBaby:0b,PersistenceRequired:1b,Tags:["m"]}}')
        game.command(combat.stats_command("@e[tag=m,limit=1]", "MILITIA"))
        game.command("team add red")
        game.command("team add blue")
        game.command(f"team join red {ship}")
        game.command(f"execute as {ship} on passengers run team join red @s")
        game.command("team join blue @e[tag=m]")
        game.command(f"aoe moveto @e[tag=m] 55.5 {y + 1} 46.5")       # 50 blocks away, across the line of fire
        time.sleep(1)
        assert "Attack: 1 units" in game.command(f"aoe attack {ship} @e[tag=m,limit=1]")
        end = time.time() + 30
        while time.time() < end and "Health" in game.command("data get entity @e[tag=m,limit=1] Health"):
            time.sleep(0.2)
        assert "Health" not in game.command("data get entity @e[tag=m,limit=1] Health"), "the walking militia lives"
