"""Xolotl Warrior (#2009): the stable of the own civilizations (game/data/civs.jsonl) trains the xolotl warrior from the
Castle Age, with the values of game/data/train.jsonl and the cost bonus of the civilization."""
import pytest
from test_castle_upgrades import STABLE, setup
from test_forging import menus

from game import civs, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
ALL = {r["name"] for r in civs.ROWS}
OWN = sorted(ALL - set(civs.MISSING["XOLOTL_WARRIOR"]))
OTHER = sorted(civs.MISSING["XOLOTL_WARRIOR"])[0]
SLOT, KIND, NAME = train.ITEMS["XOLOTL_WARRIOR"]


def stable(civ, ages=CASTLE):
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    return server, g


@pytest.mark.parametrize("civ", OWN)
def test_the_stable_of_each_own_civ_has_the_xolotl_warrior_in_the_castle_age(civ):
    server, g = stable(civ)
    train.open_menu(g, "Steve", STABLE)
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, "XOLOTL_WARRIOR").items())   # with the civ bonus
    assert f" {SLOT}:{KIND}:{NAME}:{cost} · " in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "XOLOTL_WARRIOR")


def test_another_civ_and_the_feudal_age_do_not_have_it():
    server, g = stable(OTHER)
    train.open_menu(g, "Steve", STABLE)
    assert f":{NAME}:" not in menus(server)[-1]
    server, g = stable(OWN[0], ("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    assert f"{SLOT}:{KIND}:{NAME}" not in menus(server)[-1]          # locked: a gray item
