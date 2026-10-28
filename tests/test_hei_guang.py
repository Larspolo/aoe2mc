"""Hei Guang Cavalry (#1954): the stable of the Shu, Wei and Wu trains the hei guang cavalry from the Castle Age (slot
24: 65 food, 65 gold, 28 s) and researches Heavy Hei Guang Cavalry in the Imperial Age (slot 25: 350 food, 250 gold,
70 s), with the values of the AoE2 DE wiki infoboxes "Hei Guang Cavalry" and "Heavy Hei Guang Cavalry"."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
NAMES = ("HEI_GUANG_CAVALRY", "HEAVY_HEI_GUANG_CAVALRY", "HEAVY_HEI_GUANG_CAVALRY_UPGRADE")


def stable(civ="WEI", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["hg"] = "HEI_GUANG_CAVALRY"
    g.game.entities.setdefault("hg", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for name in NAMES:
        assert len(train.HELP[name]) <= 50
        assert not {"SHU", "WEI", "WU"} & set(civs.MISSING[name]) and {"FRANKS", "BRITONS"} <= set(civs.MISSING[name])


def test_bloodlines_and_husbandry_apply_to_the_cavalry_class():
    for name in NAMES[:2]:
        s = combat.stats(name)
        assert train.TECHS["BLOODLINES"](name, s).hp == s.hp + 20
        assert train.faster("mounted", name)


def test_the_stable_menu_has_the_hei_guang_cavalry_from_the_castle_age_for_the_wei():
    server, g = stable(ages=CASTLE)
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 24:horse_spawn_egg:Hei Guang Cavalry:65 food · 65 gold · 28 s · queue 0/15 " in menu
    assert "Heavy Hei Guang" not in menu                                # the upgrade: the Imperial Age
    server, g = stable("FRANKS", CASTLE)
    train.open_menu(g, "Steve", STABLE)
    assert "Hei Guang" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    assert " 25:book:Heavy Hei Guang Cavalry:350 food · 250 gold · 70 s · research " in menus(server)[-1] + " "
    research(g, STABLE, "HEAVY_HEI_GUANG_CAVALRY_UPGRADE")
    assert g.soldiers["hg"] == "HEAVY_HEI_GUANG_CAVALRY"
    assert combat.stats_command("hg", "HEAVY_HEI_GUANG_CAVALRY", train.stats(g, "HEAVY_HEI_GUANG_CAVALRY")) in server.log   # Wei hp (#2246)
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 24:horse_spawn_egg:Heavy Hei Guang Cavalry:65 food · 65 gold · 28 s · queue 0/15 " in menu
    assert ":Hei Guang Cavalry:" not in menu and "25:book" not in menu
    assert train.queue(g, "Steve", STABLE, "HEAVY_HEI_GUANG_CAVALRY")
    assert train.queue(g, "Steve", STABLE, "HEI_GUANG_CAVALRY") is None
