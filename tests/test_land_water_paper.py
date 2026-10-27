"""AoePlugin.java (#1658): a land unit under water stays a unit (no Drowned), and a land melee unit does not take an
attack order on the crew of a ship on the water; a ranged unit does."""
import shutil
import time

import pytest

from game import combat, run


@pytest.mark.mc
def test_a_unit_does_not_drown_and_a_melee_unit_does_not_attack_a_ship(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a pool in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 16} {z0 + 16}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 12} {y + 3} {z0 + 12} stone_bricks")
        game.command(f"fill {x0} {y} {z0} {x0 + 6} {y + 3} {z0 + 6} water")
        game.command(f"summon zombie {x0 + 3.5} {y} {z0 + 3.5} {{Tags:[\"sunk\"],DrownedConversionTime:20}}")
        game.command(f"summon oak_boat {x0 + 3.5} {y + 3.5} {z0 + 5.5} "
                     "{Tags:[\"ship\"],Passengers:[{id:\"minecraft:zombie\",Tags:[\"crew\"]}]}")
        game.command(f"summon zombie {x0 + 9.5} {y + 4} {z0 + 3.5} {{Tags:[\"melee\"]}}")
        game.command(f"summon skeleton {x0 + 9.5} {y + 4} {z0 + 8.5} {{Tags:[\"archer\"]}}")
        for tag, name in (("sunk", "MILITIA"), ("crew", "TRANSPORT_SHIP"), ("melee", "MILITIA"), ("archer", "ARCHER")):
            game.command(f"tag @e[tag={tag}] add aoe2mc.p{1 + (tag == 'crew')}")
            assert "1" in game.command(combat.stats_command(f"@e[tag={tag}]", name)), tag
        time.sleep(3)
        assert "passed" in game.command("execute if entity @e[type=zombie,tag=sunk]")
        assert "failed" in game.command("execute if entity @e[type=drowned]")
        assert game.command("aoe attack @e[tag=melee] @e[tag=crew,limit=1]").strip() == "Attack: 0 units"
        assert game.command("aoe attack @e[tag=archer] @e[tag=crew,limit=1]").strip() == "Attack: 1 units"
