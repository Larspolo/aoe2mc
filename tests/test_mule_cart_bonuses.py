"""The mule cart bonuses of the Armenians (#2309, AoE2 wiki "Armenians"): mule carts cost less, and the mule cart
technologies are more effective (civs.MORE). The values come from the data: the tests compare with other civilizations.
Fake server."""
import pytest

from game import build, gather

from test_gather import FakeServer, grid


def game(civ):
    data = grid([[64] * 8 for _ in range(8)])
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    return gather.Gather(FakeServer({}), data)


def test_an_armenian_mule_cart_costs_less():
    cheap, full = build.price(game("ARMENIANS"), "MULE_CART"), build.price(game("GEORGIANS"), "MULE_CART")
    assert full == build.COSTS["MULE_CART"] and set(cheap) == set(full) and all(cheap[r] < v for r, v in full.items())


@pytest.mark.parametrize("tech, res", [("DOUBLE_BIT_AXE", "wood"), ("BOW_SAW", "wood"), ("GOLD_MINING", "gold"),
                                       ("STONE_SHAFT_MINING", "stone")])
def test_armenian_mule_cart_technologies_are_more_effective(tech, res):
    armenian, briton = game("ARMENIANS"), game("BRITONS")
    base = armenian.work_time(res)
    for g in (armenian, briton):
        g.techs.add(tech)
    assert base / armenian.work_time(res) > base / briton.work_time(res) > 1


def test_the_bonus_is_only_for_the_technologies_of_the_mule_cart():
    g = game("ARMENIANS")
    base = g.work_time("food")
    g.techs.add("HORSE_COLLAR")
    assert g.work_time("food") == base
