"""The trample damage of the elephants (#4397, AoE2 DE wiki "Trample damage"): the key "trample",
game/abilities/trample.py and `aoe trample` of the plugin. Test data, and a melee hit on a server."""
import math
import shutil
import time

import pytest
from abilities import trample
from test_mounted_attack import floor
from test_ranged import data

from game import combat, run


def test_the_trample_command_gives_the_part_and_the_radius_in_blocks(monkeypatch):
    monkeypatch.setattr(trample, "UNITS", {"TEST_ELEPHANT": {"part": 0.25, "radius": 0.4}})
    assert trample.command("u-1", "TEST_ELEPHANT", 4) == "aoe trample u-1 0.25 1.6"
    assert trample.command("u-1", "MILITIA", 4) is None


def test_a_fixed_damage_that_ignores_the_armor_holds_in_the_same_command():
    t = {"damage": 5, "radius": 0.5, "ignore": True}                  # the form of a technology (epic #4096)
    assert trample.command("u-1", "MILITIA", 4, t) == "aoe trample u-1 0 2 5 1"


def health(game, tag):
    return (data(game, tag, "Health") or [None])[0]


@pytest.mark.mc
def test_a_melee_hit_hurts_the_enemy_units_next_to_the_target(tiny_world, tmp_path, monkeypatch):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    monkeypatch.setattr(trample, "UNITS", {"TEST_ELEPHANT": {"part": 0.5, "radius": 0.6}})   # 2.4 blocks
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    hp = combat.stats("MILITIA").hp
    hit = combat.damage("ELITE_WAR_ELEPHANT", "MILITIA")
    part = max(1, math.floor(0.5 * hit + 0.5))                       # max(1, round(part × damage)), round half up
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command("time set midnight")                            # a zombie burns in the sun
        game.command(f'summon zombie {x0 + 0.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p1 @e[tag=e]")
        game.command(combat.stats_command("@e[tag=e,limit=1]", "ELITE_WAR_ELEPHANT"))
        assert game.command(trample.command("@e[tag=e,limit=1]", "TEST_ELEPHANT", 4)).strip() == "Trample: 1 units"
        for tag, team, dx, dz in (("m", "p2", 4, 4), ("n1", "p2", 5.5, 4), ("n2", "p2", 4, 5.5), ("own", "p1", 4, 2.5)):
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA"))
        assert game.command("aoe attack @e[tag=e] @e[tag=m,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and health(game, "m") == hp:
            time.sleep(0.05)
        assert health(game, "m") is not None and health(game, "m") < hp, "no hit on the target"
        lost = {tag: hp - health(game, tag) for tag in ("n1", "n2", "own")}   # before the next hit (reload 2 s)
        assert lost == pytest.approx({"n1": part, "n2": part, "own": 0}, abs=1e-3), lost
