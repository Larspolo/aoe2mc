"""The AoE2 stances "no attack" and "stand ground" (#1104): combat.stance_command and the plugin on Paper."""
import math
import shutil
import time

import pytest
from test_damage import health
from test_unit_ai import data

from game import combat, run


def test_stance_command():
    assert combat.stance_command("u-1", "no_attack") == "aoe stance u-1 no_attack"
    assert combat.stance_command("@e[tag=a]", "stand_ground") == "aoe stance @e[tag=a] stand_ground"
    with pytest.raises(ValueError):
        combat.stance_command("u-1", "hold")


@pytest.mark.mc
def test_no_attack_and_stand_ground(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 40} {z0 + 40}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 36} {y - 1} {z0 + 36} stone_bricks")
        game.command("time set midnight")
        game.command("difficulty hard")       # a skeleton aims better on hard: fewer misses
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # tag: (x, z, team, AoE2 unit). a (no attack) stands next to the enemy b; the archer s (stand ground) has t
        # in its range of 16 blocks; the archer r (stand ground) has g (and t) out of its range but in its sight of 24
        units = {"a": (2, 2, "p1", "MILITIA"), "b": (4, 2, "p2", "MILITIA"),
                 "s": (2, 14, "p1", "ARCHER"), "t": (14, 14, "p2", "MILITIA"),
                 "r": (30, 2, "p1", "ARCHER"), "g": (30, 22, "p2", "MILITIA")}
        for tag, (dx, dz, team, name) in units.items():
            mob = ('skeleton', ',equipment:{mainhand:{id:"minecraft:bow",count:1}}') if name == "ARCHER" else \
                ('zombie', ',IsBaby:0b')
            game.command(f'summon {mob[0]} {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,Tags:["{tag}"]{mob[1]}}}')
            game.command(f"team join {team} @e[tag={tag}]")
            sel = f"@e[tag={tag},limit=1]"
            assert game.command(combat.stats_command(sel, name)).strip() == "Stats: 1 units"
            if team == "p1":                  # the enemies have no sight: they do not start a fight
                stance = "no_attack" if tag == "a" else "stand_ground"
                assert game.command(combat.stance_command(sel, stance)).strip() == "Stance: 1 units"
                for cmd in (combat.range_command(sel, name, 4), combat.sight_command(sel, name, 4)):
                    if cmd:
                        game.command(cmd)
        game.command("aoe stats @e[tag=t,limit=1] 1000 0 0 0 0 infantry -")    # many hit points: it lives on
        game.command("damage @e[tag=a,limit=1] 1 minecraft:mob_attack by @e[tag=b,limit=1]")   # a hit, as from b
        assert health(game, "a") == 36.0
        start = {u: data(game, u, "Pos") for u in "sr"}
        end = time.time() + 15
        while time.time() < end and (health(game, "t") or 1000) >= 1000:
            time.sleep(0.2)
        assert health(game, "t") < 1000                                   # s shot t in its range ...
        time.sleep(3)
        for u in "sr":                                                    # ... from its place, and r stayed
            p = data(game, u, "Pos")
            assert math.hypot(p[0] - start[u][0], p[2] - start[u][2]) < 1, (u, start[u], p)
        assert health(game, "g") == 40.0                                  # g is out of the range of r
        assert health(game, "b") == 40.0                                  # a did not attack back
        assert data(game, "a", "Pos")[0] < x0 + 3.5
        # an order works with each stance: a attacks b
        assert game.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 15
        while time.time() < end and health(game, "b") == 40.0:
            time.sleep(0.2)
        assert health(game, "b") < 40.0
