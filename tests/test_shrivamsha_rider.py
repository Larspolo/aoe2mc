"""Shrivamsha Rider (#1612): the stable of the Gurjaras trains the shrivamsha rider from the Castle Age (slot 22: 70 food,
30 gold, 20 s) and researches Elite Shrivamsha Rider in the Imperial Age (slot 23: 850 food, 500 gold, 45 s), with the
values of the AoE2 DE wiki infobox "Shrivamsha Rider". The castle of the Gurjaras does not train it (its unique unit is
the chakram thrower)."""
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus

from game import civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)


def stable(civ="GURJARAS", ages=IMPERIAL):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["sr"] = "SHRIVAMSHA_RIDER"
    g.game.entities.setdefault("sr", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    for name in ("SHRIVAMSHA_RIDER", "ELITE_SHRIVAMSHA_RIDER", "ELITE_SHRIVAMSHA_RIDER_UPGRADE"):
        assert len(train.HELP[name]) <= 50 and "GURJARAS" not in civs.MISSING[name]
        assert {"BRITONS", "BENGALIS", "HINDUSTANIS"} <= set(civs.MISSING[name])


def test_the_stable_menu_has_the_shrivamsha_rider_from_the_castle_age_for_the_gurjaras():
    server, g = stable(ages=CASTLE)
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 22:horse_spawn_egg:Shrivamsha Rider:70 food · 30 gold · 20 s · queue 0/15 " in menu
    assert "Elite Shrivamsha" not in menu                               # the upgrade: the Imperial Age
    server, g = stable("BRITONS", CASTLE)
    train.open_menu(g, "Steve", STABLE)
    assert "Shrivamsha" not in menus(server)[-1]
    server, g = stable(ages=CASTLE)
    assert "SHRIVAMSHA_RIDER" not in train.trains(g, "CASTLE")          # the castle trains the chakram thrower


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = stable()
    train.open_menu(g, "Steve", STABLE)
    assert " 23:book:Elite Shrivamsha Rider:850 food · 500 gold · 45 s · research " in menus(server)[-1] + " "
    research(g, STABLE, "ELITE_SHRIVAMSHA_RIDER_UPGRADE")
    assert g.soldiers["sr"] == "ELITE_SHRIVAMSHA_RIDER"
    assert combat.stats_command("sr", "ELITE_SHRIVAMSHA_RIDER") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1] + " "
    assert " 22:horse_spawn_egg:Elite Shrivamsha Rider:70 food · 30 gold · 20 s · queue 0/15 " in menu
    assert ":Shrivamsha Rider:" not in menu and "23:book" not in menu
    assert train.queue(g, "Steve", STABLE, "ELITE_SHRIVAMSHA_RIDER")
    assert train.queue(g, "Steve", STABLE, "SHRIVAMSHA_RIDER") is None
