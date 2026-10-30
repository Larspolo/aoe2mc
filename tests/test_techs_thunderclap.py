"""Thunderclap Bombs (#4367, AoE2 DE wiki): the Rocket Carts, Lou Chuans and Grenadiers of the Jurchens explode when they
die, and the blast hurts no allied unit. A list as the value of the key "detonate" (train.FIRE) gives one value per
unit line and the word `foes` of `aoe detonate`: test data here, not the values of the data line (#4242)."""
import re
import shutil
import time

import pytest
from test_dock_train import dock_map

from game import combat, run, train

OLD = {"if": [{"names": ["FIRE_GALLEY"]}], "attack": 10, "blast": 1.5, "bonus": {"warship": 5}}      # Incendiaries form
BOMBS = [{"if": [{"names": ["GRENADIER"]}], "attack": 15, "blast": 0.75, "bonus": {}},              # test data
         {"if": [{"names": ["LOU_CHUAN"]}], "attack": 45, "blast": 2, "bonus": {"warship": 3}}]


def test_a_list_gives_each_matching_unit_its_value_with_the_foes_word(monkeypatch):
    monkeypatch.setattr(train, "FIRE", {"OLD": ("detonate", OLD), "BOMBS": ("detonate", BOMBS)})
    server, g = dock_map()
    g.techs |= {"OLD", "BOMBS"}
    T = g.map.T
    assert train.fire_commands(g, "u", "GRENADIER") == [f"aoe detonate u 15 {0.75 * T} - foes"]
    assert train.fire_commands(g, "u", "LOU_CHUAN") == [f"aoe detonate u 45 {2 * T} warship:3 foes"]
    assert train.fire_commands(g, "u", "MILITIA") == []
    assert train.fire_commands(g, "u", "FIRE_GALLEY") == [f"aoe detonate u 10 {1.5 * T} warship:5"]   # the old form
    assert train.fire_commands(g, "u", "GRENADIER", techs={"OLD"}) == []                            # no research


def health(game, uuid):
    return float(re.findall(r"(\d+\.?\d*)f", game.command(f"data get entity {uuid} Health"))[0])


@pytest.mark.mc
def test_the_blast_at_death_spares_the_own_units_on_a_server(tiny_world, tmp_path):
    from test_fire_ship import uuid_of
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a floor in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 30 30")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone_bricks")
        game.command("team add red")
        game.command("team add blue")
        ids = {}
        for name, tag, x, team in (("GRENADIER", "g", 10.5, "red"), ("MILITIA", "own", 11.5, "red"),
                                   ("MILITIA", "foe", 9.5, "blue")):
            assert "Summoned" in summon(game, name, x, y, 10.5, tag), name
            ids[tag] = uuid_of(game, tag)
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], name))
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"data merge entity {ids[tag]} {{NoAI:1b}}")
        own, foe = health(game, ids["own"]), health(game, ids["foe"])
        assert "Detonate: 1 units" in game.command(f"aoe detonate {ids['g']} 15 3.0 - foes")
        game.command(f"kill {ids['g']}")
        time.sleep(1)
        assert health(game, ids["foe"]) < foe                         # the enemy is hit
        assert health(game, ids["own"]) == own                        # the own unit is not
