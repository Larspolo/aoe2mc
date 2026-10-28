"""Steppe Lancer (#1557): the stable of the Cumans, Jurchens, Khitans, Mongols and Tatars trains the steppe lancer from the
Castle Age (slot 20: 70 food, 40 gold, 24 s) and researches Elite Steppe Lancer in the Imperial Age (slot 21: 600 food,
550 gold, 55 s), with the values of the AoE2 DE wiki infoboxes "Steppe Lancer" and "Elite Steppe Lancer". The upgrade
turns the live steppe lancers into elite ones, and the stable then trains the elite steppe lancer (20 s)."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

import units
from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def stable(civ="CUMANS", ages=IMPERIAL):   # no bonus to the hit points (the Mongols: +30 %)
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["sl"] = "STEPPE_LANCER"
    g.game.entities.setdefault("sl", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for unit in ("STEPPE_LANCER", "ELITE_STEPPE_LANCER"):
        assert len(train.HELP[unit]) <= 50
        assert units.classify(unit)["Passengers"][0]["equipment"]["mainhand"]["id"] == "minecraft:trident"
    assert len(train.HELP["ELITE_STEPPE_LANCER_UPGRADE"]) <= 50
    for civ in civs.LANCERS:
        assert civ not in civs.MISSING["STEPPE_LANCER"] and civ not in civs.MISSING["ELITE_STEPPE_LANCER_UPGRADE"]
    assert {"BRITONS", "FRANKS", "AZTECS", "TURKS"} <= set(civs.MISSING["STEPPE_LANCER"])


def test_the_stable_menu_has_the_steppe_lancer_from_the_castle_age_for_a_civ_with_it():
    server, g = stable(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    assert ":gray_dye:Steppe Lancer:70 food · 40 gold · 24 s · Needs the Castle Age" in menus(server)[-1]
    server, g = stable(ages=CASTLE)
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 20:horse_spawn_egg:Steppe Lancer:70 food · 40 gold · 24 s · queue 0/15 " in menu
    assert "Elite Steppe Lancer" not in menu                           # the upgrade: the Imperial Age
    for civ in ("BRITONS", "FRANKS"):
        server, g = stable(civ, CASTLE)
        train.open_menu(g, "Steve", STABLE)
        assert "Steppe Lancer" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    assert " 21:book:Elite Steppe Lancer:600 food · 550 gold · 55 s · research " in menus(server)[-1] + " "
    research(g, STABLE, "ELITE_STEPPE_LANCER_UPGRADE")
    assert g.soldiers["sl"] == "ELITE_STEPPE_LANCER"
    assert combat.stats_command("sl", "ELITE_STEPPE_LANCER") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 20:horse_spawn_egg:Elite Steppe Lancer:70 food · 40 gold · 20 s · queue 0/15 " in menu
    assert ":Steppe Lancer:" not in menu and "21:book" not in menu
    assert train.queue(g, "Steve", STABLE, "ELITE_STEPPE_LANCER") and train.queue(g, "Steve", STABLE, "STEPPE_LANCER") is None
