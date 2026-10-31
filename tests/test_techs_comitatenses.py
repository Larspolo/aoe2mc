"""The charge of a melee hit (#4370, Comitatenses of the Romans): the key "charge_attack" of a technology gives the own
units of its tests the plugin command `aoe chargeattack` after the research, and the plugin adds the extra attack to
the first melee hit after the charge time. Test data, not the values of the data line (owner, #4242)."""
import shutil
import time

import pytest
from test_damage import health
from test_train_castle import setup

from game import combat, gather, run, train

TECH = "COMITATENSES"                                   # a real name: train.research reads its line
CHARGE = {"if": [{"forms": ["MILITIA"]}, {"names": ["KNIGHT"]}], "attack": 3, "time": 10}


@pytest.fixture
def charge(monkeypatch):
    monkeypatch.setitem(train.FIRE, TECH, ("charge_attack", CHARGE))
    return f"{max(1, round(CHARGE['time'] / gather.NORMAL * 20))} {CHARGE['attack']}"


def test_only_a_unit_of_the_tests_gets_the_command_after_the_research(charge):
    _, g = setup("ROMANS", ages=3)
    assert train.fire_commands(g, "u", "MAN_AT_ARMS") == []                  # no research: no command
    g.techs.add(TECH)
    assert train.fire_commands(g, "u", "MAN_AT_ARMS") == [f"aoe chargeattack u {charge}"]
    assert train.fire_commands(g, "u", "KNIGHT") == [f"aoe chargeattack u {charge}"]
    assert train.fire_commands(g, "u", "ARCHER") == []


def test_the_research_sends_the_command_to_the_live_units_of_the_tests(charge):
    server, g = setup("ROMANS", ages=3)
    g.soldiers.update(u1="CHAMPION", u2="ARCHER")
    train.research(g, {"name": TECH, "player": "Steve"})
    assert [c for c in server.log if c.startswith("aoe chargeattack")] == [f"aoe chargeattack u1 {charge}"]


@pytest.mark.mc
def test_the_first_melee_hit_has_the_charge_and_the_next_one_not(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    attacker, target, extra = "MAN_AT_ARMS", "MILITIA", 4
    one = combat.damage(attacker, target)
    first = combat.damage(attacker, target, a=combat.stats(attacker)._replace(attack=combat.stats(attacker).attack + extra))
    assert first > one
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 12} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 10} {y - 1} {z0 + 10} stone_bricks")
        game.command("time set midnight")
        for tag, dx, team, name in (("a", 2, "p1", attacker), ("b", 4, "p2", target)):
            game.command(f"team add {team}")
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        assert game.command(f"aoe chargeattack @e[tag=a] 6000 {extra}").strip() == "Charge attack: 1 units"
        game.command("effect give @e[tag=b] slowness infinite 255 true")
        full = combat.stats(target).hp
        assert health(game, "b") == full
        assert game.command("aoe attack @e[tag=a] @e[tag=b,limit=1]").strip() == "Attack: 1 units"
        seen, end = [full], time.time() + 40
        while time.time() < end and len(seen) < 3:
            if (h := health(game, "b")) is not None and h != seen[-1]:
                seen.append(h)
            time.sleep(0.05)
        assert seen[:3] == [full, full - first, full - first - one], seen
