"""Bolas Rider (#2135): the Mapuche archery range trains the bolas rider from the Castle Age and researches Elite Bolas
Rider in the Imperial Age. The upgrade turns the live units into elite ones, and the archery range then trains the elite
one."""
from menu_line import item
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def archery_range(civ="MAPUCHE", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["br"] = "BOLAS_RIDER"
    g.game.entities.setdefault("br", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_menu_has_the_unit_from_the_castle_age_for_the_mapuche():
    server, g = archery_range(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", RANGE)
    line = item(menus(server)[-1], "Bolas Rider")
    assert ":gray_dye:Bolas Rider:" in line and line.endswith(text(g, "BOLAS_RIDER", "ARCHERY_RANGE") + "Needs the Castle Age")
    server, g = archery_range(ages=CASTLE)
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Bolas Rider").endswith(":Bolas Rider:" + text(g, "BOLAS_RIDER", "ARCHERY_RANGE") + "queue 0/15")
    assert "Elite Bolas Rider" not in menu                                   # the upgrade: the Imperial Age
    for civ in ("BRITONS", "INCAS"):
        server, g = archery_range(civ, CASTLE)
        train.open_menu(g, "Steve", RANGE)
        assert "Bolas Rider" not in menus(server)[-1], civ
        assert train.queue(g, "Steve", RANGE, "BOLAS_RIDER") is None, civ


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = archery_range()
    train.open_menu(g, "Steve", RANGE)
    up = item(menus(server)[-1], "Elite Bolas Rider")
    assert up.endswith(":Elite Bolas Rider:" + text(g, "ELITE_BOLAS_RIDER_UPGRADE", "ARCHERY_RANGE") + "research")
    research(g, RANGE, "ELITE_BOLAS_RIDER_UPGRADE")
    assert g.soldiers["br"] == "ELITE_BOLAS_RIDER"
    assert combat.stats_command("br", "ELITE_BOLAS_RIDER") in server.log
    train.open_menu(g, "Steve", RANGE)
    menu = menus(server)[-1] + " "
    assert item(menu, "Elite Bolas Rider").endswith(":Elite Bolas Rider:" + text(g, "ELITE_BOLAS_RIDER", "ARCHERY_RANGE") +
                                                    "queue 0/15")
    assert ":Bolas Rider:" not in menu and up not in menu
    assert train.queue(g, "Steve", RANGE, "ELITE_BOLAS_RIDER")
    assert train.queue(g, "Steve", RANGE, "BOLAS_RIDER") is None
