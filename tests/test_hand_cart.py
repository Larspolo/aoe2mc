"""game/train.py and game/gather.py: the town center researches Hand Cart in the Castle Age after Wheelbarrow (300 food
and 200 wood, 55 AoE2 seconds: AoE2 DE wiki). After it a villager carries 20 (10, 13 with Wheelbarrow: the carry table
of the wiki) and walks 10 % faster again (#1453)."""
import math

import pytest
from test_wheelbarrow import menus, setup

from game import gather, train


def castle(food=300, wood=200):
    server, g = setup(food, wood)
    g.techs |= {"CASTLE_AGE", "WHEELBARROW"}
    return server, g


def speed(server, g):
    """The movement_speed attribute of the last walk order of the villager (ai.movement_speed: the root of the walk
    speed)."""
    v = g.villagers["v"]
    v.goal = (9, 9)
    g.move(v)
    return float([c for c in server.log if c.startswith("attribute v minecraft:movement_speed ")][-1].split()[-1])


def test_the_town_center_menu_has_hand_cart_in_the_castle_age_after_wheelbarrow():
    assert train.AFTER["HAND_CART"] == "WHEELBARROW"
    server, g = setup()
    g.techs.add("WHEELBARROW")
    train.open_menu(g, "Steve", (3, 3))
    assert "Hand Cart" not in menus(server)[-1]                        # the Feudal Age
    server, g = castle()
    train.open_menu(g, "Steve", (3, 3))
    assert " 3:book:Hand Cart:300 food · 200 wood · 55 s · research" in menus(server)[-1]
    g.techs -= {"WHEELBARROW"}
    train.open_menu(g, "Steve", (3, 3))
    assert "Hand Cart" not in menus(server)[-1]


def test_a_villager_carries_20_and_walks_faster_after_hand_cart():
    server, g = castle()
    g.paper = True
    before = speed(server, g)
    assert g.limit() == 13
    train.queue(g, "Steve", (3, 3), "HAND_CART")
    train.tick(g, 54)
    assert "HAND_CART" not in g.techs
    train.tick(g, 1)
    assert "HAND_CART" in g.techs and g.limit() == 20 and g.limit("wood") == 20
    assert speed(server, g) == pytest.approx(before * math.sqrt(gather.PACE["HAND_CART"]), rel=0.002)
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
