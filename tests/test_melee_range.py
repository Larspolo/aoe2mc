"""game/combat.py and the plugin: the Throwing Axeman and the Mameluke attack from a range with melee damage, as in
AoE2: their hit takes the melee armor of the target, not the pierce armor (#800)."""
import shutil
import time

import pytest
from test_ranged import data

from game import combat, run


def test_melee_ranged_units_hit_the_melee_armor():
    target = combat.Stats(100, 1, 0, 50, 0, 2.0)                       # melee armor 0, pierce armor 50, no class
    assert combat.MELEE_RANGED
    for name in sorted(combat.MELEE_RANGED):
        t = target._replace(classes=("building",)) if name in combat.VS_UNITS else target   # anti-unit mode: pierce (#4505)
        assert combat.damage(name, "X", t=t) - combat.stats(name).bonus.get("building", 0) * (t is not target) == max(1, combat.stats(name).attack), name   # not the pierce armor
    ranged = combat.Stats(30, 6, 0, 0, 4, 2.0)
    assert combat.damage("X", "Y", a=ranged, t=target) == 1            # a ranged unit still hits the pierce armor
    assert combat.damage("X", "Y", a=ranged._replace(range=0), t=target) == 6


def test_the_plugin_gets_the_range_kind():
    melee_ranged = sorted(combat.MELEE_RANGED)[0]
    s = combat.Stats(30, 6, 0, 0, 4, 2.0)
    kinds = [combat.stats_command("u", n, v).split()[7] for n, v in (("X", s._replace(range=0)), ("X", s), (melee_ranged, s))]
    assert kinds == ["0", "1", "2"]


@pytest.mark.mc
def test_a_throwing_axeman_hits_the_melee_armor_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 8}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 28} {y - 1} {z0 + 6} stone_bricks")
        game.command("time set midnight")     # a zombie burns in daylight
        game.command("difficulty hard")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon drowned {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:trident",count:1}}}')
        game.command(f'summon zombie {x0 + 24.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        assert game.command(combat.range_command("@e[tag=a,limit=1]", "THROWING_AXEMAN", 4)).strip() == "Range: 1 units"
        assert game.command(combat.stats_command("@e[tag=a,limit=1]", "THROWING_AXEMAN")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 6 0 infantry -")    # melee armor 0, pierce armor 6
        assert game.command("aoe attack @e[tag=a] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        drops, last, end = [], 1000.0, time.time() + 40
        while time.time() < end and len(drops) < 3:
            h = (data(game, "t", "Health") or [last])[0]
            if h < last:
                drops.append(round(last - h, 1))
                last = h
            time.sleep(0.05)
        attack = combat.stats("THROWING_AXEMAN").attack
        assert drops and set(drops) == {float(attack)}, drops          # attack - 0, not max(1, attack - 6)
