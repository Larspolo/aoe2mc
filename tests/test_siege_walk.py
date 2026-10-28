"""Siege units (minecarts with a crew) walk to an order on a carrier mob of the plugin (#836)."""
import math
import shutil
import time

import numpy as np
import pytest
from nbtlib import serialize_tag
from nbtlib.tag import List, String
from test_unit_ai import data

import units
from game import ai, run


def test_siege_units_are_minecarts():
    assert all(units.siege(n) for n in ("BATTERING_RAM", "COBRA_CAR", "MANGONEL", "TREBUCHET"))
    assert not any(units.siege(n) for n in ("MILITIA", "KNIGHT", "WAR_GALLEY", "PETARD", "VILLAGER_MALE", "WAR_WAGON"))


def test_the_speed_of_a_siege_unit_goes_through_the_plugin():
    assert ai.speed_command("u", "BATTERING_RAM", 4) == f"aoe speed u {ai.movement_speed('BATTERING_RAM', 4)}"
    assert ai.speed_command("u", "MILITIA", 4).startswith("attribute u minecraft:movement_speed base set ")


def summon(game, name, x, y, z, tag):
    """Summon the converter's entity of unit name (a minecart with its crew) with a tag."""
    nbt = units.to_nbt(units.classify(name), (x, y, z), 0.0, np.random.default_rng(len(tag)))   # own UUIDs
    kind = nbt.pop("id")
    for k in ("Pos", "UUID"):
        nbt.pop(k, None)
    nbt["Tags"] = List[String]([String(tag)])
    return game.command(f"summon {kind} {x} {y} {z} {serialize_tag(nbt)}")


@pytest.mark.mc
def test_a_ram_and_a_cobra_car_drive_to_an_order(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 12} stone_bricks")
        game.command(f"fill {x0 + 12} {y} {z0 - 1} {x0 + 26} {y} {z0 + 12} stone_bricks")   # a step of one block
        for name, tag, dz in (("BATTERING_RAM", "ram", 2), ("COBRA_CAR", "cobra", 8)):
            assert "Summoned" in summon(game, name, x0 + 2.5, y, z0 + dz + 0.5, tag), name
            sel = f"@e[type=minecart,tag={tag}]"
            assert game.command(ai.speed_command(sel, name, 4)).strip() == "Speed: 1 units"
            assert game.command(f"aoe moveto {sel} {x0 + 20.5} {y + 1} {z0 + dz + 0.5}").strip() == "Moved 1 units"
        assert game.command("aoe stats @e[type=minecart,tag=ram] 175 2 0 180 0 - -").strip() == "Stats: 1 units"
        end, near = time.time() + 30, {}
        while time.time() < end and len(near) < 2:
            time.sleep(1)
            for tag, dz in (("ram", 2), ("cobra", 8)):
                p = data(game, tag, "Pos")
                if p and math.dist((p[0], p[2]), (x0 + 20.5, z0 + dz + 0.5)) < 2 and p[1] >= y + 1:
                    near[tag] = p
        assert set(near) == {"ram", "cobra"}, (data(game, "ram", "Pos"), data(game, "cobra", "Pos"))
        time.sleep(5)
        for tag, dz in (("ram", 2), ("cobra", 8)):                     # it stays there: no slide after the walk
            p = data(game, tag, "Pos")
            assert math.dist((p[0], p[2]), (x0 + 20.5, z0 + dz + 0.5)) < 2.5, (tag, p)
        assert "Count: 2" in game.command("execute if entity @e[tag=aoe2mc.carrier]")       # one pig for each
        crew = game.command("execute as @e[type=minecart,tag=ram,limit=1] on passengers run "   # the attribute list is
                            "attribute @s minecraft:max_health base get")      # too long for the data output (#1664)
        assert "175" in crew                                           # aoe stats: the crew has the AoE2 hit points
        assert game.command("aoe stop @e[type=minecart,tag=ram]").strip() == "Stopped 1 units"
