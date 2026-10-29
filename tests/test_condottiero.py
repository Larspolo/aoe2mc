"""Condottiero (#2156): the barracks of the Italians and of their allies (civs.SHARED, the team bonus) trains the
condottiero in the Imperial Age."""
from test_castle_upgrades import BARRACKS, entry, setup
from test_forging import menus

from game import train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def menu(civ, other="FRANKS", other_team=1, ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ, "team": 1}, "2": {"civ": other, "team": other_team}}
    train.open_menu(g, "Steve", BARRACKS)
    return server, g, menus(server)[-1]


def test_the_help_text_is_short():
    assert len(train.HELP["CONDOTTIERO"]) <= 50


def test_an_italian_player_trains_it_in_the_imperial_age():
    server, g, text = menu("ITALIANS", ages=IMPERIAL[:2])
    assert entry(g, BARRACKS, "CONDOTTIERO") + "Needs the Imperial Age" in text
    server, g, text = menu("ITALIANS")
    assert " " + entry(g, BARRACKS, "CONDOTTIERO") + "queue 0/15" in text
    assert train.queue(g, "Steve", BARRACKS, "CONDOTTIERO")


def test_an_ally_of_an_italian_player_trains_it_and_an_enemy_does_not():
    assert "Condottiero" in menu("BRITONS", "ITALIANS")[2]
    for other, team in (("ITALIANS", 2), ("FRANKS", 1)):
        server, g, text = menu("BRITONS", other, team)
        assert "Condottiero" not in text and not train.queue(g, "Steve", BARRACKS, "CONDOTTIERO")
