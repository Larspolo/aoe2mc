"""Hoplite (#2431): the Athenian, Spartan and Thracian barracks trains the hoplite from the Castle (Classical) Age, and
the Athenians and Spartans research Elite Hoplite (the Imperial Age, the Spartans one age earlier). Athenian hoplites
walk faster. Values of the AoE2 wiki "Hoplite (Chronicles)". Not here: the armor aura of a pair of hoplites."""
import pytest
from menu_line import item
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def upgrade(m):
    """True when the menu m has Elite Hoplite as a research."""
    return (item(m, "Elite Hoplite") or "").endswith(" · research")


def barracks(civ="ATHENIANS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["h"] = "HOPLITE"
    g.game.entities.setdefault("h", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def menu(civ, ages):
    server, g = barracks(civ, ages)
    train.open_menu(g, "Steve", BARRACKS)
    return menus(server)[-1] + " "


def test_the_menu_has_the_unit_from_the_castle_age():
    assert item(menu("ATHENIANS", ("FEUDAL_AGE",)), "Hoplite").endswith(" · Needs the Castle Age")
    m = menu("THRACIANS", IMPERIAL)
    assert item(m, "Hoplite").endswith(" · queue 0/15") and "Elite Hoplite" not in m
    for civ in ("BRITONS", "ACHAEMENIDS", "MACEDONIANS"):
        assert "Hoplite" not in menu(civ, CASTLE), civ


def test_the_spartans_research_the_elite_hoplite_one_age_earlier():
    assert "Elite Hoplite" not in menu("ATHENIANS", CASTLE)                 # the upgrade: the Imperial Age
    assert upgrade(menu("SPARTANS", CASTLE))
    assert upgrade(menu("ATHENIANS", IMPERIAL))


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks("SPARTANS", CASTLE)
    research(g, BARRACKS, "ELITE_HOPLITE_UPGRADE")
    assert g.soldiers["h"] == "ELITE_HOPLITE"
    assert combat.stats_command("h", "ELITE_HOPLITE", T=g.map.T) in server.log
    train.open_menu(g, "Steve", BARRACKS)
    m = menus(server)[-1]
    assert item(m, "Elite Hoplite").endswith(" · queue 0/15") and item(m, "Hoplite") is None
    assert train.queue(g, "Steve", BARRACKS, "ELITE_HOPLITE")


@pytest.mark.parametrize("unit", ["HOPLITE", "ELITE_HOPLITE"])
def test_an_athenian_hoplite_walks_faster(unit):
    _, athenian = barracks("ATHENIANS")
    _, spartan = barracks("SPARTANS")
    assert train.speed(athenian, unit) > train.speed(spartan, unit)
    assert train.speed(athenian, "MILITIA") == train.speed(spartan, "MILITIA")
