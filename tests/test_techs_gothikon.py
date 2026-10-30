"""Gothikon (#4368, AoE2 DE wiki): the Varangian Guards throw charged axes at their target. The key "throw" of a
technology of data/train.jsonl gives the matching own units the plugin command `aoe throw` (train.fire_commands): a
test line here, not the values of the data line (#4242). The plugin: a server."""
import shutil
import time

import pytest
from test_train_castle import setup

from game import combat, gather, run, train

AXES = {"if": [{"names": ["MILITIA"]}], "reload": 12, "gap": 0.5, "range": 2, "shots": 3}   # a test line


def ticks(seconds):
    return max(1, round(seconds / gather.NORMAL * 20))


def throws(server):
    return [c for c in server.log if c.startswith("aoe throw ")]


def test_only_a_unit_of_the_tests_gets_the_axes_after_the_research(monkeypatch):
    monkeypatch.setitem(train.BY_KEY, "throw", {"GOTHIKON": AXES})
    server, g = setup("VARANGIANS", ages=3)
    assert train.fire_commands(g, "u", "MILITIA") == []                    # no research: no axes
    g.techs.add("GOTHIKON")
    assert train.fire_commands(g, "u", "MILITIA") == \
        [f"aoe throw u {ticks(12)} {ticks(0.5)} {2 * g.map.T:g} 3"]        # charge, gap, range in blocks, axes
    assert train.fire_commands(g, "u", "ARCHER") == []                     # not in the tests
    assert train.fire_commands(g, "u", "MILITIA", {"SIPHONS"}) == []       # only the techs of the call


def test_the_research_gives_the_live_units_the_axes_and_a_new_unit_too(monkeypatch):
    monkeypatch.setitem(train.BY_KEY, "throw", {"GOTHIKON": AXES})
    server, g = setup("VARANGIANS", ages=3)
    g.soldiers.update({"m": "MILITIA", "a": "ARCHER"})
    train.research(g, {"name": "GOTHIKON", "player": "Steve"})
    assert throws(server) == train.fire_commands(g, "m", "MILITIA")
    new = train.summon(g, "MILITIA", (12.5, 64.0, 9.5))
    assert throws(server)[1:] == train.fire_commands(g, new, "MILITIA")
    train.summon(g, "ARCHER", (12.5, 64.0, 9.5))
    assert len(throws(server)) == 2


@pytest.mark.mc
def test_a_unit_with_axes_hurts_an_enemy_out_of_its_reach(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_damage import health
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 30}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 26} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        # tag: (x, z, team, AoE2 unit); g throws at m, h (no axes) cannot reach n, 8 blocks away
        units = {"g": (2, 2, "p1", "VARANGIAN_GUARD"), "m": (10, 2, "p2", "MILITIA"),
                 "h": (2, 14, "p1", "VARANGIAN_GUARD"), "n": (10, 14, "p2", "MILITIA")}
        for tag, (dx, dz, team, name) in units.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + dz + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
            game.command(f"attribute @e[tag={tag},limit=1] minecraft:movement_speed base set 0")   # a hit one hits back
        assert game.command("aoe throw @e[tag=g] 2000 20 12 2").strip() == "Throw: 1 units"   # 2 axes, no charge
        for a, t in (("g", "m"), ("h", "n")):
            assert game.command(f"aoe attack @e[tag={a}] @e[tag={t},limit=1]").strip() == "Attack: 1 units"
        time.sleep(5)
        hp, hit = combat.stats("MILITIA").hp, combat.damage("VARANGIAN_GUARD", "MILITIA")
        assert health(game, "m") == hp - 2 * hit                          # two axes, then the charge is long
        assert health(game, "n") == hp                                    # no axes: out of its melee reach
