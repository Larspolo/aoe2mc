"""Imperial Camel Rider (#2013): the stable of the Hindustanis researches Imperial Camel Rider in the Imperial Age after
Heavy Camel Rider (in its slot, the "UUpCost" of the AoE2 DE wiki page "Heavy Camel Rider"). It turns the live heavy
camel riders into imperial ones, and the stable then trains the imperial camel rider (the wiki infobox "Imperial Camel
Rider")."""
from menu_line import item
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def stable(civ="HINDUSTANIS", techs=("HEAVY_CAMEL_RIDER_UPGRADE",)):
    server, g = setup(ages=IMPERIAL, techs=techs)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["hc"] = "HEAVY_CAMEL_RIDER"
    g.game.entities.setdefault("hc", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_only_the_hindustanis_see_it_after_heavy_camel_rider():
    server, g = stable(techs=())
    train.open_menu(g, "Steve", STABLE)
    heavy = item(menus(server)[-1], "Heavy Camel Rider")
    assert heavy.split(":")[1] == "book" and "Imperial Camel Rider" not in menus(server)[-1]
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    imperial = item(menus(server)[-1], "Imperial Camel Rider")
    assert imperial.split(":")[0] == heavy.split(":")[0] and imperial.endswith(" · research")   # in the same slot
    server, g = stable("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Imperial Camel Rider" not in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "IMPERIAL_CAMEL_RIDER_UPGRADE") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    research(g, STABLE, "IMPERIAL_CAMEL_RIDER_UPGRADE")
    assert g.soldiers["hc"] == "IMPERIAL_CAMEL_RIDER"
    assert any(c.startswith(f"aoe stats hc {train.stats(g, 'IMPERIAL_CAMEL_RIDER').hp} ") for c in server.log)
    assert train.stats(g, "IMPERIAL_CAMEL_RIDER").reload < combat.stats("IMPERIAL_CAMEL_RIDER").reload   # the Hindustani bonus
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert item(menu, "Imperial Camel Rider").endswith(" · queue 0/15")
    assert item(menu, "Heavy Camel Rider") is None                     # no unit and no research
    assert train.queue(g, "Steve", STABLE, "IMPERIAL_CAMEL_RIDER")
    assert train.queue(g, "Steve", STABLE, "HEAVY_CAMEL_RIDER") is None
