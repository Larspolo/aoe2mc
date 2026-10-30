"""The charged volley of a melee unit (#4547, the Fire Lancer): the optional "range" and "ignore" of the key
"charged_volley" give the extra fields of aoe chargedvolley; the plugin fires the volley at the target in the range
before the melee. Test data, and a Paper server."""
import shutil
import time

import pytest
from test_damage import health

from game import combat, run

VOLLEY = {"time": 30, "shots": 3, "attack": 3, "bonus": {"ram": 2}}


def test_range_and_ignore_give_the_extra_fields(monkeypatch):
    monkeypatch.setattr(combat, "CHARGED_VOLLEY", {"MILITIA": {**VOLLEY, "range": 4, "ignore": True}})
    assert combat.charged_volley_command("u", "MILITIA", 4).endswith(" 3 3 ram:2 16 1")


def test_a_key_without_them_gives_the_short_command(monkeypatch):
    monkeypatch.setattr(combat, "CHARGED_VOLLEY", {"MILITIA": VOLLEY})
    assert combat.charged_volley_command("u", "MILITIA", 4).endswith(" 3 3 ram:2")


@pytest.mark.mc
def test_a_melee_unit_hurts_a_target_in_the_range_through_the_armor(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as g:
        g.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 16} {z0 + 12}")
        g.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 15} {y - 1} {z0 + 10} stone_bricks")
        g.command("time set midnight")
        for tag, dx, team in (("a", 1, "p1"), ("b", 13, "p2")):       # 12 blocks: 3 tiles at T = 4
            g.command(f"team add {team}")
            g.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            g.command(f"team join {team} @e[tag={tag}]")
            assert g.command(combat.stats_command(f"@e[tag={tag},limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        assert g.command("aoe chargedvolley @e[tag=a] 6000 3 3 - 16 1").strip() == "Charged volley: 1 units"
        full = combat.stats("MILITIA").hp
        assert combat.stats("MILITIA").pierce > 0                     # the armor that the shots ignore
        assert g.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        time.sleep(2)
        assert health(g, "b") == full - 3 * 3                         # once: the charge starts again
