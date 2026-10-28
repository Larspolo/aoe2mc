"""Xolotl Warrior (#2009): the stable of the Aztecs, Incas, Mapuche, Mayans, Muisca and Tupi trains the xolotl warrior
from the Castle Age (slot 26: 60 food, 75 gold, 30 s), with the values of the AoE2 DE wiki infobox "Xolotl Warrior"."""
import pytest
from test_castle_upgrades import STABLE, setup
from test_forging import menus

from game import build, civs, train

import units

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
OWN = ("AZTECS", "INCAS", "MAPUCHE", "MAYANS", "MUISCA", "TUPI")


def stable(civ, ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


def test_the_values_are_those_of_aoe2():
    assert build.AGE["XOLOTL_WARRIOR"] == 2 and train.ITEMS["XOLOTL_WARRIOR"][0] == train.MORE + 8
    assert len(train.HELP["XOLOTL_WARRIOR"]) <= 50
    assert not set(OWN) & set(civs.MISSING["XOLOTL_WARRIOR"]) and {"FRANKS", "SHU"} <= set(civs.MISSING["XOLOTL_WARRIOR"])
    assert str(units.classify("XOLOTL_WARRIOR")["id"]) == "minecraft:horse"   # a rider on a horse, as the knight


@pytest.mark.parametrize("civ", OWN)
def test_the_stable_of_each_own_civ_has_the_xolotl_warrior_in_the_castle_age(civ):
    server, g = stable(civ)
    train.open_menu(g, "Steve", STABLE)
    cost = "45 food" if civ == "INCAS" else "60 food"                   # the Incas: their food bonus (civs.jsonl)
    assert f" 26:horse_spawn_egg:Xolotl Warrior:{cost} · 75 gold · " in menus(server)[-1]   # the Aztecs train faster
    assert train.queue(g, "Steve", STABLE, "XOLOTL_WARRIOR")


def test_the_franks_and_the_feudal_age_do_not_have_it():
    server, g = stable("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Xolotl" not in menus(server)[-1]
    server, g = stable("AZTECS", ("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    assert "26:horse_spawn_egg:Xolotl Warrior" not in menus(server)[-1]   # locked: a gray item
