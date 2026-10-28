"""The mule cart bonuses of the Armenians (#2309, AoE2 wiki "Armenians"): mule carts cost -25 %, mule cart technologies
are 40 % more effective (Double-Bit Axe and Bow Saw +28 % in place of +20 %, the mining technologies +21 % in place of
+15 %). Fake server."""
import pytest

from game import build, civs, gather

from test_gather import FakeServer, grid


def game(civ):
    data = grid([[64] * 8 for _ in range(8)])
    data["players"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}
    return gather.Gather(FakeServer({}), data)


def test_an_armenian_mule_cart_costs_25_percent_less():
    assert build.price(game("ARMENIANS"), "MULE_CART") == {r: round(v * 0.75) for r, v in build.COSTS["MULE_CART"].items()}
    assert build.price(game("GEORGIANS"), "MULE_CART") == build.COSTS["MULE_CART"]


@pytest.mark.parametrize("tech, res, gain", [("DOUBLE_BIT_AXE", "wood", 1.28), ("BOW_SAW", "wood", 1.28),
                                             ("GOLD_MINING", "gold", 1.21), ("STONE_SHAFT_MINING", "stone", 1.21)])
def test_armenian_mule_cart_technologies_are_40_percent_more_effective(tech, res, gain):
    armenian, briton = game("ARMENIANS"), game("BRITONS")
    base = armenian.work_time(res)
    for g in (armenian, briton):
        g.techs.add(tech)
    assert base / armenian.work_time(res) == pytest.approx(gain)
    assert base / briton.work_time(res) == pytest.approx(1 + (gain - 1) / 1.4)


def test_the_bonus_is_only_for_the_technologies_of_the_mule_cart():
    assert set(civs.MORE["ARMENIANS"]) == {"BOW_SAW", "DOUBLE_BIT_AXE", "GOLD_MINING", "GOLD_SHAFT_MINING",
                                           "STONE_MINING", "STONE_SHAFT_MINING"}   # no Two-Man Saw: Armenians miss it
    g = game("ARMENIANS")
    base = g.work_time("food")
    g.techs.add("HORSE_COLLAR")
    assert g.work_time("food") == base
