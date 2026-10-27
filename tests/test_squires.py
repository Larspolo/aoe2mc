"""game/train.py: the barracks researches Squires in the Castle Age (100 food, 40 s, AoE2 DE wiki infobox): the live
and the new infantry of the player walk 10 % faster, other units do not change (#1415)."""
import re

import pytest
from test_forging import menus, setup

from game import ai, civs, gather, train

BARRACKS = (17, 3)


def castle(food=100):
    server, g = setup(food=food)
    g.techs.add("CASTLE_AGE")
    return server, g


def test_the_cost_time_and_age_are_those_of_aoe2():
    assert train.TECH_AGE["SQUIRES"] == 2 and train.HELP["SQUIRES"] and "SQUIRES" in train.TRAINS["BARRACKS"]
    assert "CELTS" in civs.MISSING["SQUIRES"]                                  # the wiki availability chart


def test_before_the_castle_age_the_barracks_has_no_squires():
    server, g = setup()
    train.open_menu(g, "Steve", BARRACKS)
    assert "Squires" not in menus(server)[-1]


def test_the_barracks_menu_has_squires_in_the_castle_age():
    server, g = castle()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 4:book:Squires:100 food · 40 s · research " in menus(server)[-1] + " "


def test_squires_makes_the_live_and_the_new_infantry_walk_10_percent_faster():
    server, g = castle(food=160)
    g.stock["gold"] = 20
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.speed(g, "MILITIA") == 1
    assert train.order(g, "Steve", rect, 4) == 1 and g.stock["food"] == 60
    server.log.clear()
    train.tick(g, 40)
    assert "SQUIRES" in g.techs and "Squires is researched." in " ".join(server.log)
    assert train.speed(g, "MILITIA") == pytest.approx(1.1) and train.speed(g, "SPEARMAN") == pytest.approx(1.1)
    assert train.speed(g, "SCOUT_CAVALRY") == train.speed(g, "ARCHER") == train.speed(g, "VILLAGER_MALE") == 1
    assert ai.speed_command("m", "MILITIA", g.map.T, gather.NORMAL * 1.1) in server.log           # the live militia
    assert not any(c.startswith(("aoe speed s ", "aoe speed a ")) for c in server.log)              # not the others
    assert train.order(g, "Steve", rect, 0) == 1                                                    # a new militia
    new, = train.tick(g, train.TRAIN_TIMES["MILITIA"])
    assert any(re.fullmatch(re.escape(ai.speed_command(new, "MILITIA", g.map.T, gather.NORMAL * 1.1)), c) for c in server.log)
