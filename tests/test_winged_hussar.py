"""Winged Hussar (#1558): the own civilizations (game/data/civs.jsonl) upgrade the light cavalry to the winged hussar at
the stable in the Imperial Age, in place of the hussar upgrade, with the values of game/data/train.jsonl. Then the live
light cavalry are winged hussars and the stable trains the winged hussar. The other civilizations do not see it."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus
from test_urumi_swordsman import item, label

from game import civs, combat, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
ALL = {r["name"] for r in civs.ROWS}
OWN = sorted(ALL - set(civs.MISSING["WINGED_HUSSAR_UPGRADE"]))
OTHER = sorted(ALL - set(civs.MISSING["HUSSAR_UPGRADE"]) - set(OWN))[0]   # a civilization with the hussar


def imperial(civ):
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": civ}}
    research(g, STABLE, "LIGHT_CAVALRY_UPGRADE")
    train.open_menu(g, "Steve", STABLE)
    return server, g


def test_the_own_civs_see_it_in_place_of_hussar():
    for civ in OWN:
        server, g = imperial(civ)
        menu = menus(server)[-1] + " "
        assert item(g, "WINGED_HUSSAR_UPGRADE", "research") in menu and f":{label('HUSSAR_UPGRADE')}:" not in menu


def test_other_civs_see_the_hussar_only():
    server, _ = imperial(OTHER)
    menu = menus(server)[-1]
    slot, kind, name = train.ITEMS["HUSSAR_UPGRADE"]
    assert f":{label('WINGED_HUSSAR_UPGRADE')}:" not in menu and f" {slot}:{kind}:{name}:" in " " + menu
    server, g = setup(ages=IMPERIAL)
    g.data["players"] = {"1": {"civ": OWN[0]}}
    train.open_menu(g, "Steve", STABLE)
    assert f":{label('WINGED_HUSSAR_UPGRADE')}:" not in menus(server)[-1]   # not before Light Cavalry


def test_the_live_light_cavalry_become_winged_hussars_and_the_stable_trains_them():
    server, g = imperial(OWN[0])
    assert g.soldiers["l"] == "LIGHT_CAVALRY"
    research(g, STABLE, "WINGED_HUSSAR_UPGRADE")
    assert g.soldiers["l"] == "WINGED_HUSSAR"
    assert combat.stats_command("l", "WINGED_HUSSAR") in server.log
    assert combat.label_command("l", "WINGED_HUSSAR") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert item(g, "WINGED_HUSSAR", f"queue 0/{train.QUEUE}") in menu and f":{label('LIGHT_CAVALRY')}:" not in menu
    assert train.queue(g, "Steve", STABLE, "WINGED_HUSSAR")
    assert train.queue(g, "Steve", STABLE, "LIGHT_CAVALRY") is None
