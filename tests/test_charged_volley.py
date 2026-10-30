"""The charged volley of a ranged unit (#4546, the Xianbei Raider): the key "charged_volley" of data/units.jsonl sends
the plugin command aoe chargedvolley for each new unit. Test data, fake server of test_gather."""
import shutil
import time

import pytest
from abilities import charged_volley
from test_damage import health
from test_kill_spoils import game

from game import combat, gather, run, train

VOLLEY = {"time": 30, "shots": 5, "attack": 1, "bonus": {"spearman": 4, "infantry": 1}}


def volley(monkeypatch):
    monkeypatch.setattr(charged_volley, "UNITS", {"ARCHER": VOLLEY})


def test_a_new_unit_with_the_key_gets_its_charged_volley(monkeypatch):
    volley(monkeypatch)
    server, g = game("BRITONS")
    u = train.summon(g, "ARCHER", (8.5, 64.0, 8.5))
    ticks = round(VOLLEY["time"] / gather.NORMAL * 20)
    assert f"aoe chargedvolley {u} {ticks} 5 1 infantry:1,spearman:4" in server.log


def test_a_unit_without_the_key_gets_none(monkeypatch):
    volley(monkeypatch)
    server, g = game("BRITONS")
    train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    assert not any(c.startswith("aoe chargedvolley") for c in server.log)
    assert charged_volley.command("u", "MILITIA") is None


@pytest.mark.mc
def test_the_first_shot_with_a_full_charge_hurts_more_than_the_next(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    shooter, target = "ARCHER", "MILITIA"
    with run.Game(world) as g:
        g.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        g.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        g.command("time set midnight")
        for tag, dx, team, mob, name in (("a", 1, "p1", "skeleton", shooter), ("b", 7, "p2", "zombie", target)):
            g.command(f"team add {team}")
            g.command(f'summon {mob} {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            g.command(f"team join {team} @e[tag={tag}]")
            assert g.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        assert g.command(combat.range_command("@e[tag=a,limit=1]", shooter, 4)).strip() == "Range: 1 units"
        assert g.command("aoe chargedvolley @e[tag=a] 6000 5 1 infantry:1").strip() == "Charged volley: 1 units"
        g.command("effect give @e[tag=b] slowness infinite 255 true")
        full = combat.stats(target).hp
        assert health(g, "b") == full
        assert g.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        seen, end = [full], time.time() + 40
        while time.time() < end and len(seen) < 4:
            if (h := health(g, "b")) is not None and h != seen[-1]:
                seen.append(h)
            time.sleep(0.05)
        drops = [round(a - b) for a, b in zip(seen, seen[1:])]
        assert len(drops) == 3 and drops[0] > max(drops[1:]), seen    # the volley comes with the first shot only
