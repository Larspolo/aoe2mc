"""The extra projectiles of a technology (#4338: Hul'che Javelineers, Double Crossbow, Bolt Magazine, Sitting Tiger):
the key "volley" of data/train.jsonl, train.volley_command and `aoe volley` of the plugin, also for a siege shot.
Test data, not the data lines (owner, 2026-10-29, #4242). Fake server, and a Scorpion on a server."""
import shutil
import time

import pytest
from test_dock_train import dock_map

import train as plain_train          # build and gather import train by its plain name (not game.train)
from game import ai, combat, run, train

TECH = {"SCORPION": {"shots": 1, "part": 0.5}, "ARCHER": {"shots": 2}, "SKIRMISHER": {"shots": 1, "attack": 1}}


@pytest.fixture
def tech(monkeypatch):
    for module in (plain_train, train):
        monkeypatch.setitem(module.BY_KEY["volley"], "TEST_TECH", TECH)
        monkeypatch.setitem(module.TECHS, "TEST_TECH", lambda name, s: s)              # no change of the values
    server, g = dock_map()
    return server, g


def test_each_unit_of_the_key_gets_its_shots_and_attack(tech):
    server, g = tech
    g.techs.add("TEST_TECH")
    assert train.volley_command(g, "u", "ARCHER") == "aoe volley u 2 0"                # the full attack
    assert train.volley_command(g, "u", "SKIRMISHER") == "aoe volley u 1 1"
    half = max(1, round(train.stats(g, "SCORPION").attack * 0.5))
    assert train.volley_command(g, "u", "SCORPION") == f"aoe volley u 1 {half}"
    assert train.volley_command(g, "u", "KNIGHT") is None


def test_with_no_research_a_unit_fires_one_projectile(tech):
    server, g = tech
    assert all(train.volley_command(g, "u", name) is None for name in TECH)


def test_the_research_gives_the_live_units_their_extra_projectiles(tech):
    server, g = tech
    uuid = train.summon(g, "ARCHER", (5.5, 64.0, 12.5))
    knight = train.summon(g, "KNIGHT", (6.5, 64.0, 12.5))
    del server.log[:]
    train.research(g, {"name": "TEST_TECH", "player": 1}, start=True)                 # no text of a menu item
    assert f"aoe volley {uuid} 2 0" in server.log
    assert not any(c.startswith(f"aoe volley {knight}") for c in server.log)


def test_each_volley_of_the_data_names_known_units_and_a_count():
    for tech_name, units in plain_train.BY_KEY["volley"].items():
        for name, v in units.items():
            assert name in combat.STATS, (tech_name, name)
            assert isinstance(v["shots"], int) and v["shots"] > 0, (tech_name, name)
            assert not ("attack" in v and "part" in v), (tech_name, name)


@pytest.mark.mc
def test_a_scorpion_with_a_volley_hits_twice_in_one_reload_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_ranged import data
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 10}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 28} {y - 1} {z0 + 8} stone_bricks")
        game.command("time set midnight")                                         # the zombie must not burn
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "SCORPION", x0 + 1.5, y, z0 + 4.5, "s")
        s = "@e[type=minecart,tag=s,limit=1]"
        game.command(f'summon zombie {x0 + 18.5} {y} {z0 + 4.5} {{NoAI:1b,IsBaby:0b,Tags:["m1"]}}')
        game.command("team join p2 @e[tag=m1]")
        game.command("aoe stats @e[tag=m1,limit=1] 1000 4 0 1 0 infantry -")         # militia values
        game.command(f"team join p1 {s}")
        assert game.command(combat.stats_command(s, "SCORPION")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(s, "SCORPION", 4)).strip() == "Range: 1 units"
        v = combat.stats("SCORPION")
        half = max(1, round(v.attack * 0.5))
        assert game.command(f"aoe volley {s} 1 {half}").strip() == "Volley: 1 units"
        game.command(ai.speed_command(s, "SCORPION", 4))
        assert game.command(f"aoe attack {s} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m1", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        game.command(f"aoe stop {s}")                                             # no second reload
        time.sleep(0.5)
        hp = (data(game, "m1", "Health") or [None])[0]
        hit = v.attack + v.bonus.get("infantry", 0) - 1                            # 1 pierce armor
        assert hp == 1000.0 - hit - max(1, half - 1), hp                         # the extra bolt: no bonus
