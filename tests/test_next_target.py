"""After their building falls, rams take the next enemy building in sight, other units do not (#1820, owner decision:
the AoE2 wiki "Siege unit (Age of Empires II)"): `aoe sight ... only|first` (combat.BUILDING_SIGHT)."""
import shutil
import time

import pytest

from game import ai, combat, run
from test_building_damage import hp
from test_siege_walk import summon
from test_unit_ai import data


def test_the_units_of_building_sight_take_buildings_in_sight():
    assert set(combat.BUILDING_SIGHT) <= set(combat.STATS)
    for name, mode in combat.BUILDING_SIGHT.items():
        assert mode in ("only", "first"), name
        assert combat.sight_command("u", name, 4) == f"aoe sight u {combat.sight(name) * 4} {mode}", name
    assert combat.sight_command("u", "MILITIA", 4) == f"aoe sight u {combat.sight('MILITIA') * 4}"   # units only (#775)
    assert combat.sight_command("u", "SIEGE_TOWER", 4) is None                  # no attack


@pytest.mark.mc
def test_a_ram_takes_the_next_house_and_militia_stay(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                         # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 40 50")
        game.command(f"fill 0 {y - 1} 0 39 {y - 1} 47 stone_bricks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # house a falls; b is 5 blocks south of it; c, far away, is next to the ram nn with the stance "no attack"
        houses = {"a": (20, 8), "b": (20, 16), "c": (20, 38)}
        uuids = {}
        for k, (x, z) in houses.items():
            game.command(f"fill {x} {y} {z} {x + 2} {y + 2} {z + 2} oak_planks")
            uuids[k] = combat.target_uuid([x, z, x + 3, z + 3])
            s = combat.stats("HOUSE")._replace(hp=200) if k == "a" else None
            for c in combat.building(uuids[k], "HOUSE", 2, (x, y, z, x + 2, y + 2, z + 2), s=s):
                game.command(c)
        full = hp(game, uuids["b"])
        for tag, (x, z) in {"r": (14.5, 9.5), "nn": (14.5, 39.5)}.items():
            assert "Summoned" in summon(game, "BATTERING_RAM", x, y, z, tag)
            r = f"@e[type=minecart,tag={tag},limit=1]"
            game.command(f"team join p1 {r}")
            assert game.command(combat.stats_command(r, "BATTERING_RAM")).strip() == "Stats: 1 units"
            assert game.command(combat.range_command(r, "BATTERING_RAM", 4)).strip() == "Range: 1 units"
            game.command(ai.speed_command(r, "BATTERING_RAM", 4))
            assert game.command(combat.sight_command(r, "BATTERING_RAM", 4)).strip() == "Sight: 1 units"
        assert game.command("aoe stance @e[type=minecart,tag=nn] no_attack").strip() == "Stance: 1 units"
        for i in range(3):
            game.command(f'summon zombie {16.5 + i} {y} 6.5 {{NoAI:1b,IsBaby:0b,Tags:["m"]}}')
        game.command("team join p1 @e[tag=m]")
        assert game.command(combat.stats_command("@e[tag=m]", "MILITIA")).strip() == "Stats: 3 units"
        assert game.command(combat.sight_command("@e[tag=m]", "MILITIA", 4)).strip() == "Sight: 3 units"
        assert game.command(f"aoe attack @e[type=minecart,tag=r] {uuids['a']}").strip() == "Attack: 1 units"
        assert game.command(f"aoe attack @e[tag=m] {uuids['a']}").strip() == "Attack: 3 units"
        end = time.time() + 60
        while time.time() < end and hp(game, uuids["a"]) is not None:
            time.sleep(0.2)
        assert hp(game, uuids["a"]) is None                               # house a fell
        ram, end = combat.damage("BATTERING_RAM", "HOUSE"), time.time() + 30
        while time.time() < end and hp(game, uuids["b"]) > full - 2 * ram:
            time.sleep(0.2)
        assert (full - hp(game, uuids["b"])) % ram == 0 and hp(game, uuids["b"]) <= full - 2 * ram   # only the ram hits b
        time.sleep(5)              # the militia stay: b still takes only ram hits (the ram can push them on its way)
        assert (full - hp(game, uuids["b"])) % ram == 0, hp(game, uuids["b"])
        assert combat.damage("MILITIA", "HOUSE") % ram
        assert hp(game, uuids["c"]) == full                               # no attack: the ram nn stays
        p = data(game, "nn", "Pos")
        assert p and abs(p[0] - 14.5) < 1 and abs(p[2] - 39.5) < 1, p
