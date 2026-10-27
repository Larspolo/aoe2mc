"""Fire Lancer (#1953): the barracks of the Chinese, Jurchens, Khitans, Koreans and Vietnamese trains the fire lancer from
the Castle Age (slot 19: 45 wood, 45 gold, 35 s) and researches Elite Fire Lancer in the Imperial Age (slot 20: 750 food,
400 gold, 50 s), with the values of the AoE2 DE wiki infoboxes "Fire Lancer (Age of Empires II)" and "Elite Fire
Lancer". The upgrade turns the live fire lancers into elite ones, and the barracks then trains the elite one (25 s)."""
from test_castle_upgrades import BARRACKS, research, setup
from test_forging import menus

import units
from game import build, civs, combat, replay, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def barracks(civ="JURCHENS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["fl"] = "FIRE_LANCER"
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["FIRE_LANCER"] == train.COSTS["ELITE_FIRE_LANCER"] == {"wood": 45, "gold": 45}
    assert train.TRAIN_TIMES["FIRE_LANCER"] == 35 and train.TRAIN_TIMES["ELITE_FIRE_LANCER"] == 25
    assert train.COSTS["ELITE_FIRE_LANCER_UPGRADE"] == {"food": 750, "gold": 400}
    assert train.TRAIN_TIMES["ELITE_FIRE_LANCER_UPGRADE"] == 50 and train.TECH_AGE["ELITE_FIRE_LANCER_UPGRADE"] == 3
    assert build.AGE["FIRE_LANCER"] == 2 and build.AGE["ELITE_FIRE_LANCER"] == 3
    assert combat.stats("ELITE_FIRE_LANCER") == (85, 10, 2, 1, 0, 2.0, {"building": 1, "cavalry": 15, "camel": 12,
                                                                      "elephant": 15}, ("infantry", "gunpowder"))
    assert combat.sight("FIRE_LANCER") == 7 and combat.sight("ELITE_FIRE_LANCER") == 8
    for unit in ("FIRE_LANCER", "ELITE_FIRE_LANCER"):
        assert replay.SPEEDS[unit] == 0.96 and len(train.HELP[unit]) <= 50
        assert units.classify(unit)["id"] == "minecraft:pillager"
    assert len(train.HELP["ELITE_FIRE_LANCER_UPGRADE"]) <= 50
    assert train.ITEMS["FIRE_LANCER"][0] == train.ITEMS["ELITE_FIRE_LANCER"][0] == train.MORE + 1
    assert train.ITEMS["ELITE_FIRE_LANCER_UPGRADE"][0] == train.MORE + 2
    for civ in civs.FIRE_LANCERS:
        assert civ not in civs.MISSING["FIRE_LANCER"] and civ not in civs.MISSING["ELITE_FIRE_LANCER_UPGRADE"]
    assert {"BRITONS", "FRANKS", "MONGOLS", "TURKS"} <= set(civs.MISSING["FIRE_LANCER"])


def test_the_barracks_menu_has_the_fire_lancer_from_the_castle_age_for_a_civ_with_it():
    server, g = barracks(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", BARRACKS)
    assert ":gray_dye:Fire Lancer:45 wood · 45 gold · 35 s · Needs the Castle Age" in menus(server)[-1]
    server, g = barracks("CHINESE", CASTLE)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 19:pillager_spawn_egg:Fire Lancer:45 wood · 45 gold · 35 s · queue 0/15 " in menu
    assert "Elite Fire Lancer" not in menu                             # the upgrade: the Imperial Age
    for civ in ("BRITONS", "FRANKS"):
        server, g = barracks(civ, CASTLE)
        train.open_menu(g, "Steve", BARRACKS)
        assert "Fire Lancer" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, "FIRE_LANCER") is None


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = barracks()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 20:book:Elite Fire Lancer:750 food · 400 gold · 50 s · research " in menus(server)[-1] + " "
    research(g, BARRACKS, "ELITE_FIRE_LANCER_UPGRADE")
    assert g.soldiers["fl"] == "ELITE_FIRE_LANCER"
    assert combat.stats_command("fl", "ELITE_FIRE_LANCER") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1] + " "
    assert " 19:pillager_spawn_egg:Elite Fire Lancer:45 wood · 45 gold · 25 s · queue 0/15 " in menu
    assert ":Fire Lancer:" not in menu and "20:book" not in menu
    assert train.queue(g, "Steve", BARRACKS, "ELITE_FIRE_LANCER") and train.queue(g, "Steve", BARRACKS, "FIRE_LANCER") is None


def test_gambesons_adds_its_pierce_armor():
    server, g = barracks()
    old = {n: train.stats(g, n) for n in ("FIRE_LANCER", "ELITE_FIRE_LANCER")}
    research(g, BARRACKS, "GAMBESONS")
    for n in old:
        assert train.stats(g, n) == old[n]._replace(pierce=old[n].pierce + 1)
