"""Imperial Camel Rider (#2013): the stable of the Hindustanis researches Imperial Camel Rider in the Imperial Age after
Heavy Camel Rider (slot 18: 1000 food, 500 gold, 125 s, the "UUpCost" of the AoE2 DE wiki page "Heavy Camel Rider").
It turns the live heavy camel riders into imperial ones, and the stable then trains the imperial camel rider (55 food,
60 gold, 20 s, 140 hit points: the wiki infobox "Imperial Camel Rider")."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def stable(civ="HINDUSTANIS", techs=("HEAVY_CAMEL_RIDER_UPGRADE",)):
    server, g = setup(ages=IMPERIAL, techs=techs)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["hc"] = "HEAVY_CAMEL_RIDER"
    g.game.entities.setdefault("hc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["after"]["IMPERIAL_CAMEL_RIDER_UPGRADE"] == "HEAVY_CAMEL_RIDER_UPGRADE"
    assert len(train.HELP["IMPERIAL_CAMEL_RIDER_UPGRADE"]) <= 50
    assert civs.MISSING["IMPERIAL_CAMEL_RIDER_UPGRADE"] == tuple(sorted({r["name"] for r in civs.ROWS} - {"HINDUSTANIS"}))


def test_only_the_hindustanis_see_it_after_heavy_camel_rider():
    server, g = stable(techs=())
    train.open_menu(g, "Steve", STABLE)
    assert " 18:book:Heavy Camel Rider:" in menus(server)[-1] and "Imperial Camel Rider" not in menus(server)[-1]
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    assert " 18:book:Imperial Camel Rider:1000 food · 500 gold · 125 s · research " in menus(server)[-1] + " "
    server, g = stable("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Imperial Camel Rider" not in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "IMPERIAL_CAMEL_RIDER_UPGRADE") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    research(g, STABLE, "IMPERIAL_CAMEL_RIDER_UPGRADE")
    assert g.soldiers["hc"] == "IMPERIAL_CAMEL_RIDER"
    assert any(c.startswith("aoe stats hc 140 ") for c in server.log)
    assert train.stats(g, "IMPERIAL_CAMEL_RIDER").reload == 1.667     # the Hindustani bonus: 2 / 1.2
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 6:camel_spawn_egg:Imperial Camel Rider:55 food · 60 gold · 20 s · queue 0/15 " in menu
    assert ":Heavy Camel Rider:" not in menu and "18:book" not in menu
    assert train.queue(g, "Steve", STABLE, "IMPERIAL_CAMEL_RIDER")
    assert train.queue(g, "Steve", STABLE, "HEAVY_CAMEL_RIDER") is None
