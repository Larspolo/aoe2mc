"""Genitour (#1610): the archery range of the Berbers trains the genitour from the Castle Age and researches Elite
Genitour in the Imperial Age. The upgrade turns the live genitours into elite ones, and the archery range then trains
the elite genitour. The Berber cavalry bonus (civs.COSTS) also makes the genitour cheaper, as on the wiki."""
from menu_line import item
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def archery(civ="BERBERS", ages=IMPERIAL):
    server, g = setup(ages=ages, techs=())
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["ge"] = "GENITOUR"
    g.game.entities.setdefault("ge", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_archery_range_has_the_genitour_from_the_castle_age_for_the_berbers():
    server, g = archery(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Genitour").endswith(" · Needs the Castle Age")
    server, g = archery(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Genitour").endswith(" · queue 0/15")
    cost, base = train.price(g, "GENITOUR"), train.COSTS["GENITOUR"]
    assert all(cost[r] < v for r, v in base.items() if v)              # the Berber cavalry bonus
    assert item(menu, "Elite Genitour") is None                        # the upgrade: the Imperial Age
    for civ in ("BRITONS", "FRANKS"):
        server, g = archery(civ, IMPERIAL)
        train.open_menu(g, "Steve", RANGE)
        assert "Genitour" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery()
    train.open_menu(g, "Steve", RANGE)
    assert item(menus(server)[-1], "Elite Genitour").endswith(" · research")
    research(g, RANGE, "ELITE_GENITOUR_UPGRADE")
    assert g.soldiers["ge"] == "ELITE_GENITOUR"
    assert combat.stats_command("ge", "ELITE_GENITOUR") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1]
    assert item(menu, "Elite Genitour").endswith(" · queue 0/15")
    assert item(menu, "Genitour") is None                              # only the elite unit
    assert train.queue(g, "Steve", RANGE, "ELITE_GENITOUR") and train.queue(g, "Steve", RANGE, "GENITOUR") is None
