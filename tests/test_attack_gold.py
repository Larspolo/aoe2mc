"""The gold of the Varangian Guard (#2376, AoE2 DE wiki): 35 gold for each AoE2 minute that it attacks enemy units, the
Varangians 50 % more. The plugin counts gold per minute × reload ticks of each hit on an enemy unit in the score
aoe_attack_gold of the team (AoePlugin.gold). Fake server of test_gather."""
import shutil
import time

import pytest
from test_kill_spoils import game
from test_mounted_attack import floor
from test_ranged import data

from game import combat, run, spoils, train

TICKS = 720 * 35          # 720 real ticks of hits at Normal speed (61.2 AoE2 seconds) of a unit with 35 gold per minute


def score(server, n):
    command = server.command
    server.command = lambda c: (f"p1 has {n['n']} [{spoils.GOLD}]"
                                if c == f"scoreboard players get p1 {spoils.GOLD}" else command(c))


@pytest.mark.parametrize("civ, gold", [("VIKINGS", 35), ("VARANGIANS", 53)])   # 35 × 61.2 / 60, 1.5 times as much
def test_a_varangian_guard_makes_gold_while_it_attacks(civ, gold):
    server, g = game(civ)
    u = train.summon(g, "VARANGIAN_GUARD", (8.5, 64.0, 8.5))
    assert f"tag {u} add aoe2mc.gold.35" in server.log                 # the plugin counts its hits
    n = {"n": 0}
    score(server, n)
    train.census(g)
    assert g.stock["gold"] == 0                                        # no hit yet
    n["n"] = TICKS
    train.census(g)
    train.census(g)                                                    # the same hits give gold only once
    assert g.stock["gold"] == gold


def test_no_guard_sends_no_command():
    server, g = game("VARANGIANS")
    train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    train.census(g)
    assert f"scoreboard players get p1 {spoils.GOLD}" not in server.log
    assert not any("aoe2mc.gold" in c for c in server.log)


@pytest.mark.mc
def test_the_plugin_counts_the_hits_of_a_gold_unit_on_enemy_units(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    get = f"scoreboard players get p1 {spoils.GOLD}"
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command(f'summon zombie {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["g"]}}')
        game.command("team join p1 @e[tag=g]")
        game.command(combat.stats_command("@e[tag=g,limit=1]", "VARANGIAN_GUARD"))
        game.command(spoils.tag_command("@e[tag=g,limit=1]", "VARANGIAN_GUARD"))
        game.command(f'summon zombie {x0 + 3.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["m"]}}')
        game.command("team join p2 @e[tag=m]")
        game.command(combat.stats_command("@e[tag=m,limit=1]", "MILITIA"))
        assert game.command("aoe attack @e[tag=g] @e[tag=m,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and data(game, "m", "Health") is not None:
            time.sleep(0.1)
        assert data(game, "m", "Health") is None, "the militia is alive"
        reload = int(combat.stats_command("u", "VARANGIAN_GUARD").split()[10])
        hits = int(game.command(get).split("has ")[1].split()[0]) // (35 * reload)
        assert hits >= 3, game.command(get)            # 40 hit points, 13 damage a hit: 4 hits
