"""Siphons and Incendiaries (#2165, AoE2 DE wiki): after Siphons, a fire galley line ship that hits a ship also hits the
units near it with a charge attack (melee 2, 7 projectiles, blast radius 0.5 tiles, +1 vs. long-range warships and
buildings) each 25 s. After Incendiaries, a fire galley line ship that sinks detonates (melee 10, +5 vs. long-range
warships, blast width 3 tiles). The plugin commands `aoe charge` and `aoe detonate`: fake server, and a server."""
import shutil
import time

import pytest
from test_dock_train import DOCK, dock_map
from test_fire_ship import health, uuid_of
from test_train_archery import menus

from game import combat, gather, run, train


def test_the_values_are_those_of_the_wiki():
    kind, c = train.FIRE["SIPHONS"]
    assert kind == "charge" and (c["reload"], c["attack"], c["shots"], c["blast"]) == (25, 2, 7, 0.5)
    assert c["bonus"] == {"building": 1, "warship": 1}
    kind, c = train.FIRE["INCENDIARIES"]
    assert kind == "detonate" and (c["attack"], c["blast"], c["bonus"]) == (10, 1.5, {"warship": 5})


def test_only_the_fire_galley_line_gets_the_commands_after_the_research():
    server, g = dock_map()
    assert train.fire_commands(g, "u", "FIRE_GALLEY") == []                 # no research: nothing changes
    g.techs |= {"SIPHONS", "INCENDIARIES"}
    ticks = round(25 / gather.NORMAL * 20)
    for name in ("FIRE_GALLEY", "FIRE_SHIP", "FAST_FIRE_SHIP"):              # tile size 1: blast in blocks = tiles
        assert train.fire_commands(g, "u", name) == [f"aoe charge u {ticks} 2 7 0.5 building:1,warship:1",
                                                     "aoe detonate u 10 1.5 warship:5"]
    for name in ("GALLEY", "DEMOLITION_SHIP", "HULK", "DRAGON_SHIP"):
        assert train.fire_commands(g, "u", name) == [], name


def test_the_research_gives_the_live_fire_ships_the_charge_and_a_new_one_too():
    server, g = dock_map(wood=400)
    g.techs, g.stock["gold"] = {"FEUDAL_AGE"}, 200
    train.open_menu(g, "Steve", (15, 12))
    assert ":Fire Galley:" in menus(server)[-1]
    assert train.order(g, "Steve", DOCK, 6) == 1
    fire, = train.tick(g, 49)
    assert not [c for c in server.log if c.startswith(("aoe charge", "aoe detonate"))]
    train.research(g, {"name": "SIPHONS", "player": "Steve"})
    assert [c for c in server.log if c.startswith("aoe charge")] == [c for c in train.fire_commands(g, fire, "FIRE_GALLEY")]
    assert not [c for c in server.log if c.startswith("aoe detonate")]
    train.research(g, {"name": "INCENDIARIES", "player": "Steve"})
    assert len([c for c in server.log if c.startswith("aoe charge")]) == 1      # not again
    assert [c for c in server.log if c.startswith("aoe detonate")] == [f"aoe detonate {fire} 10 1.5 warship:5"]
    new = train.summon(g, "FIRE_GALLEY", (14.5, 63.0, 2.5))
    assert set(train.fire_commands(g, new, "FIRE_GALLEY")) <= set(server.log)


@pytest.mark.mc
def test_the_charge_and_the_detonation_hurt_the_ships_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 50 30")
        game.command(f"fill 0 {y - 1} 0 47 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 45 {y} 21 water")
        game.command("team add red")
        ids = {}
        for name, tag, x, z in (("FIRE_GALLEY", "f", 6.5, 5.5), ("GALLEY", "gg", 12.5, 5.5),       # the charge
                                ("FISHING_SHIP", "nnn", 14.0, 5.5),   # 1.5 blocks away, not in the line of the galley shots (#3890)
                                ("FIRE_GALLEY", "pppp", 30.5, 5.5), ("GALLEY", "qqqqq", 36.5, 5.5),  # no charge
                                ("FIRE_GALLEY", "dddddd", 6.5, 16.5), ("GALLEY", "hhhhhhh", 10.5, 16.5)):   # detonation
            assert "Summoned" in summon(game, name, x, y + 0.5, z, tag), name
            ids[tag] = uuid_of(game, tag)
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], name))     # the crew
        for tag in ("f", "pppp", "dddddd"):
            game.command(f"team join red @e[tag={tag}]")
            game.command(f"execute as {ids[tag]} on passengers run team join red @s")
            assert "Range: 1 units" in game.command(f"aoe range {ids[tag]} 10.0 400 0")   # one plain hit in 20 s
        assert "Charge: 1 units" in game.command(f"aoe charge {ids['f']} 400 2 7 2.0 building:1,warship:1")
        assert "Detonate: 1 units" in game.command(f"aoe detonate {ids['dddddd']} 10 6.0 warship:5")
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['f']} {ids['gg']}")
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['pppp']} {ids['qqqqq']}")
        time.sleep(3)
        assert health(game, ids["qqqqq"]) == 110 - 3                    # the plain hit: melee 2, +1 vs. warships
        assert health(game, ids["gg"]) == 110 - 3 - 7 * 3               # and 7 charge projectiles of 2 + 1
        assert health(game, ids["nnn"]) == 50 - 7 * 1                   # melee armor 1, no warship
        game.command(f"execute as {ids['dddddd']} on passengers run kill @s")
        time.sleep(1)
        assert "Test failed" in game.command(f"execute if entity {ids['dddddd']}")         # it sank
        assert health(game, ids["hhhhhhh"]) == 110 - 15                 # melee 10, +5 vs. warships
        assert health(game, ids["nnn"]) == 50 - 7                       # 13 blocks away: out of the blast of 6
