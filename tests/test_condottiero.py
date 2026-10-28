"""Condottiero (#2156): the barracks of the Italians and of their allies (civs.SHARED, the team bonus) trains the
condottiero in the Imperial Age (slot 29: 50 food, 35 gold, 18 s), with the values of the AoE2 DE wiki infobox
"Condottiero (Age of Empires II)" (MediaWiki API, 2026-10-27: 80 HP, 10 attack, 1/0 armor, sight 8, speed 1.2)."""
from test_castle_upgrades import BARRACKS, setup
from test_forging import menus

import units
from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
UNIT = 29                                                              # after the Ibirapema Warrior upgrade (28)


def menu(civ, other="FRANKS", other_team=1, ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ, "team": 1}, "2": {"civ": other, "team": other_team}}
    train.open_menu(g, "Steve", BARRACKS)
    return server, g, menus(server)[-1]


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["CONDOTTIERO"]) <= 50                         # cost, time and age: the menu tests
    assert units.classify("CONDOTTIERO")["id"] == "minecraft:zombie"     # combat values and speed: data files (#2223)
    assert set(civs.MISSING["CONDOTTIERO"]) == {r["name"] for r in civs.ROWS} - {"ITALIANS"}


def test_an_italian_player_trains_it_in_the_imperial_age():
    server, g, text = menu("ITALIANS", ages=IMPERIAL[:2])
    assert ":gray_dye:Condottiero:50 food · 35 gold · 18 s · Needs the Imperial Age" in text
    server, g, text = menu("ITALIANS")
    assert f" {UNIT}:zombie_spawn_egg:Condottiero:50 food · 35 gold · 18 s · queue 0/15" in text
    assert train.queue(g, "Steve", BARRACKS, "CONDOTTIERO")


def test_an_ally_of_an_italian_player_trains_it_and_an_enemy_does_not():
    assert "Condottiero" in menu("BRITONS", "ITALIANS")[2]
    for other, team in (("ITALIANS", 2), ("FRANKS", 1)):
        server, g, text = menu("BRITONS", other, team)
        assert "Condottiero" not in text and not train.queue(g, "Steve", BARRACKS, "CONDOTTIERO")
