"""The blast of a charged hit (#4544, the Urumi Swordsman): a "blast" {"part", "radius"} in the key "charge_attack" of
data/units.jsonl adds part and radius in blocks to `aoe chargeattack`; the charged hit also hurts the near enemy
units. Test data, and melee hits on a server."""
import shutil
import time

import pytest
from abilities import charge as ability
from test_mounted_attack import floor
from test_trample import health

from game import combat, run

BLAST = {"time": 24, "attack": 12, "blast": {"part": 0.5, "radius": 0.75}}


def charge(monkeypatch, c):
    monkeypatch.setattr(ability, "UNITS", {"MILITIA": c})


def test_a_blast_adds_the_part_and_the_radius_in_blocks(monkeypatch):
    charge(monkeypatch, BLAST)
    assert ability.command("u", "MILITIA", 4).endswith(" 0.5 3")


def test_a_charge_without_a_blast_is_as_before(monkeypatch):
    charge(monkeypatch, {"time": 24, "attack": 12})
    ticks = round(24 / combat.NORMAL * 20)
    assert ability.command("u", "MILITIA", 4) == f"aoe chargeattack u {ticks} 12"


@pytest.mark.mc
def test_a_charged_hit_hurts_a_near_enemy_unit_and_an_uncharged_hit_does_not(tiny_world, tmp_path, monkeypatch):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    charge(monkeypatch, {"time": 1000, "attack": 12, "blast": {"part": 0.5, "radius": 0.75}})   # one charge only
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    hp = combat.stats("MILITIA").hp
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command("time set midnight")                            # a zombie burns in the sun
        game.command(f'summon zombie {x0 + 0.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["u"]}}')
        game.command("team join p1 @e[tag=u]")
        game.command(combat.stats_command("@e[tag=u,limit=1]", "MILITIA"))
        assert game.command(ability.command("@e[tag=u,limit=1]", "MILITIA", 4)).strip() == "Charge attack: 1 units"
        for tag, dx in (("m", 4), ("n", 5.5)):                       # n: 1.5 blocks from the target (blast: 3)
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA"))
        assert game.command("aoe attack @e[tag=u] @e[tag=m,limit=1]").strip() == "Attack: 1 units"
        seen = []
        end = time.time() + 30
        while time.time() < end and len(seen) < 2:                    # the charged hit, then an uncharged hit
            m = health(game, "m")
            if m is not None and m < (seen[-1][0] if seen else hp):
                seen.append((m, health(game, "n")))
            time.sleep(0.05)
        assert len(seen) == 2, seen
        assert seen[0][1] < hp, "the charged hit does not hurt the near unit"
        assert seen[1][1] == pytest.approx(seen[0][1], abs=1e-3), "an uncharged hit hurts the near unit"
