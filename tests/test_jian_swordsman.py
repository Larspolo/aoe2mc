"""Jian Swordsman (#2134): the barracks of the Wu trains the Jian Swordsman from the Castle Age (slot 25: 45 food,
50 gold, 35 s), with the values of the AoE2 DE wiki infobox "Jian Swordsman" (the shielded form: 70 HP, 8 attack,
0/5 armor, +4 vs. archers, +2 vs. buildings). It has no elite upgrade. The switch to the unshielded form at 45 HP is
not here."""
from test_castle_upgrades import BARRACKS, setup
from test_forging import menus

import units
from game import build, civs, combat, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def barracks(civ="WU", ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", BARRACKS)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert build.AGE["JIAN_SWORDSMAN"] == 2 and len(train.HELP["JIAN_SWORDSMAN"]) <= 50
    s = combat.stats("JIAN_SWORDSMAN")
    assert (s.hp, s.attack, s.melee, s.pierce, s.reload) == (70, 8, 0, 5, 2.0)
    assert s.bonus == {"archer": 4, "building": 2} and "infantry" in s.classes
    assert units.classify("JIAN_SWORDSMAN")["id"] == "minecraft:zombie"
    assert "WU" not in civs.MISSING["JIAN_SWORDSMAN"]
    assert set(civs.MISSING["JIAN_SWORDSMAN"]) == {r["name"] for r in civs.ROWS} - {"WU"}


def test_a_wu_player_trains_it_in_the_castle_age():
    server, _ = barracks(ages=("FEUDAL_AGE",))
    assert ":gray_dye:Jian Swordsman:45 food · 50 gold · 35 s · Needs the Castle Age" in menus(server)[-1]
    server, g = barracks()
    assert " 25:zombie_spawn_egg:Jian Swordsman:45 food · 50 gold · 35 s · queue 0/15 " in menus(server)[-1] + " "
    assert train.queue(g, "Steve", BARRACKS, "JIAN_SWORDSMAN")


def test_other_civilizations_do_not_see_it():
    for civ in ("SHU", "FRANKS"):
        server, g = barracks(civ)
        assert "Jian Swordsman" not in menus(server)[-1]
        assert train.queue(g, "Steve", BARRACKS, "JIAN_SWORDSMAN") is None
