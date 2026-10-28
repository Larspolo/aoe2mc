"""Towers and idle units attack ships and siege units (#3015): the AoE2 values of a ship or a siege unit are on its
crew, which rides the boat or the minecart. towers() and watch() of the plugin skip only a unit on a horse with values
(the horse is the target). Servers."""
import re
import shutil
import time

import pytest
from test_siege_walk import summon

from game import combat, run


def uuid_of(game, sel):
    ints = [int(i) for i in re.findall(r"-?\d+", game.command(f"data get entity {sel} UUID").rsplit(":", 1)[-1])]
    h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def hp(game, sel):
    """The health of the passenger of sel (a crew or a rider), None when it is gone."""
    m = re.findall(r"(-?\d+\.?\d*)f", game.command(f"execute as {sel} on passengers run data get entity @s Health"))
    return float(m[0]) if m else None


def health(game, sel):
    m = re.findall(r"(-?\d+\.?\d*)f", game.command(f"data get entity {sel} Health"))
    return float(m[0]) if m else None


def unit(game, name, x, y, z, tag, team):
    """A converted unit of the converter (a boat or a minecart with its crew) of team, with its values on the crew."""
    assert "Summoned" in summon(game, name, x, y, z, tag), name
    root = f"@e[tag={tag},limit=1]"
    game.command(f"team join {team} {root}")
    game.command(f"execute as {root} on passengers run team join {team} @s")
    u = uuid_of(game, root)
    assert "Stats: 1 units" in game.command(combat.stats_command(u, name))
    return u


def militia(game, x, y, z, tag):
    game.command(f'summon zombie {x} {y} {z} {{IsBaby:0b,Tags:["{tag}"]}}')
    game.command(f"team join p1 @e[tag={tag}]")
    assert "Stats: 1 units" in game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA"))
    assert "Sight: 1 units" in game.command(combat.sight_command(f"@e[tag={tag},limit=1]", "MILITIA", 4))


def wait(test, seconds):
    end = time.time() + seconds
    while time.time() < end and not test():
        time.sleep(0.5)
    return test()


@pytest.fixture
def game(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as g:
        g.command("forceload add -2 -2 80 80")
        g.command("time set midnight")
        for t in ("p1", "p2"):
            g.command(f"team add {t}")
        yield g


@pytest.mark.mc
def test_a_tower_shoots_the_crew_of_a_galley_and_the_horse_of_a_knight(game):
    y = 200
    game.command(f"fill 0 {y - 1} 0 47 {y} 47 stone_bricks")
    game.command(f"fill 2 {y} 2 21 {y} 21 water")
    unit(game, "GALLEY", 10.5, y + 0.5, 10.5, "g", "p2")
    game.command(f"fill 30 {y} 30 47 {y} 47 air")
    box = (24, y, 24, 27, y + 12, 27)                       # 1 x 1 tile, the galley 4 blocks from its corner
    for c in combat.building(combat.target_uuid([24, 24, 28, 28]), "WATCH_TOWER", 1, box):
        game.command(c)
    h = hp(game, "@e[type=oak_boat,tag=g]")
    assert h is not None
    assert wait(lambda: (hp(game, "@e[type=oak_boat,tag=g]") or 0) < h, 20), "the tower shoots the galley"
    game.command("kill @e[tag=g]")
    game.command("execute as @e[type=oak_boat] on passengers run kill @s")
    game.command(f'summon horse 34.5 {y + 1} 34.5 {{NoAI:1b,Tame:1b,Tags:["k"],Passengers:[{{id:"minecraft:zombie",'
                 f'NoAI:1b,Tags:["kr"]}}]}}')
    game.command("team join p2 @e[tag=k]")
    game.command("team join p2 @e[tag=kr]")
    for tag in ("k", "kr"):
        assert "Stats: 1 units" in game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "KNIGHT"))
    h, r = health(game, "@e[tag=k,limit=1]"), health(game, "@e[tag=kr,limit=1]")
    assert wait(lambda: (health(game, "@e[tag=k,limit=1]") or 0) < h, 20), "the tower shoots the horse"
    assert health(game, "@e[tag=kr,limit=1]") == r, "not the rider"


@pytest.mark.mc
def test_idle_units_attack_a_ram_and_galleys_fight_but_militia_stays_off_a_ship(game):
    y = 200
    game.command(f"fill 0 {y - 1} 0 60 {y - 1} 60 stone_bricks")
    game.command(f"fill 0 {y} 30 60 {y} 60 stone_bricks")
    game.command(f"fill 2 {y} 32 40 {y} 58 water")
    unit(game, "BATTERING_RAM", 10.5, y, 10.5, "ramm", "p2")
    militia(game, 4.5, y, 10.5, "m")
    a = unit(game, "GALLEY", 10.5, y + 0.5, 40.5, "ga", "p1")
    b = unit(game, "GALLEY", 24.5, y + 0.5, 40.5, "gbb", "p2")
    for u in (a, b):
        assert "Range: 1 units" in game.command(combat.range_command(u, "GALLEY", 4))
        assert "Sight: 1 units" in game.command(combat.sight_command(u, "GALLEY", 4))
    ha = hb = combat.stats("GALLEY").hp
    assert wait(lambda: (hp(game, "@e[tag=ga,limit=1]") or 0) < ha and (hp(game, "@e[tag=gbb,limit=1]") or 0) < hb,
                40), "the galleys fight with no order"
    h = hp(game, "@e[tag=ramm,limit=1]")
    assert h is not None and wait(lambda: (hp(game, "@e[tag=ramm,limit=1]") or 0) < h, 30), "the militia hits the ram"
    militia(game, 26.5, y + 1, 30.5, "s")                   # on the shore, 10 blocks from the enemy galley
    time.sleep(8)
    m = re.findall(r"-?\d+\.\d+", game.command("data get entity @e[tag=s,limit=1] Pos"))
    assert m and float(m[2]) < 32, "the militia on the shore does not walk into the water to a galley"
