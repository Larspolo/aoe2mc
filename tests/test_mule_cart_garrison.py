"""game/garrison.py: a mule cart garrisons in an own town center, tower or castle, and a damaged cart inside gets its
hit points back for free: a share of its hit points per AoE2 minute (garrison.REPAIR: more in a castle), CART_HERBAL
times as fast after Herbal Medicine (AoE2 DE wiki "Mule Cart", #2505)."""
import pytest
import test_garrison_game as game
from test_garrison_heal import CASTLE, TC, run, setup

from game import garrison

SHARE, MORE = garrison.REPAIR["MULE_CART"]


def test_a_selected_mule_cart_garrisons_in_an_own_town_center_on_a_click():
    server, g = game.setup(villagers=1)
    server.entities["cart"] = {"Pos": (8.5, 64.0, 9.5)}
    g.soldiers["cart"] = "MULE_CART"
    g.choose({"cart"}, "cart")
    assert garrison.order(g, "Steve", (3, 3)) == game.TC
    game.arrive(server, g, game.TC)
    assert g.garrisons == {game.TC: ["cart"]} and "tag cart add aoe2mc.garrisoned" in server.log


def test_a_villager_still_garrisons_as_before():
    server, g = game.setup(villagers=1)
    g.choose({"v0"}, "v0")
    assert garrison.order(g, "Steve", (3, 3)) == game.TC
    game.arrive(server, g, game.TC)
    assert g.garrisons == {game.TC: ["v0"]} and g.villagers["v0"].state == "garrison"


def test_a_damaged_cart_gets_its_share_a_minute_in_a_town_center_and_a_castle_for_free():
    server, g = setup(("a", "MULE_CART", TC, 30.0, 300.0), ("b", "MULE_CART", CASTLE, 30.0, 300.0))
    stock = dict(g.stock)
    run(g, 60)
    assert server.entities["a"]["Health"] == pytest.approx(30 + MORE.get("TOWN_CENTER", SHARE) * 300)
    assert server.entities["b"]["Health"] == pytest.approx(30 + MORE.get("CASTLE", SHARE) * 300)
    assert g.stock == stock                                        # no resources are paid
    run(g, 600)
    assert server.entities["a"]["Health"] == 300.0 and server.entities["b"]["Health"] == 300.0


def test_herbal_medicine_repairs_a_cart_three_times_as_fast():
    server, g = setup(("a", "MULE_CART", TC, 30.0, 300.0), ("m", "MILITIA", TC, 10.0, 40.0))
    g.techs.add("HERBAL_MEDICINE")
    run(g, 10)
    assert server.entities["a"]["Health"] == pytest.approx(30 + garrison.CART_HERBAL * MORE.get("TOWN_CENTER", SHARE) * 300 / 6)
    assert server.entities["m"]["Health"] == pytest.approx(10 + garrison.HERBAL * 0.1 * 10)   # a unit: as before
