"""game/train.py: an Armenian or Georgian player researches the lumber camp and mining camp technologies at the mule
cart, as in AoE2 DE (AoE2 wiki "Mule Cart": "Research technologies", #2208). The mining camp items are in the slots right
of the lumber camp items."""
from urllib.parse import unquote

import pytest
from menu_line import item, labels, order
from test_gather import FakeServer, grid

from game import gather, train


def setup(civ="ARMENIANS"):
    """A flat 16 × 16 map (tile size 1): a mule cart of player 1 (civ) at blocks x 2-3, z 2-3 and a villager."""
    objects = [{"kind": "building", "name": "MULE_CART", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.stock.update(food=1000, wood=1000)
    g.techs.add("FEUDAL_AGE")
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_mule_cart_menu_has_the_lumber_and_mining_camp_technologies():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Mule Cart ") and labels(cmd) == order(g, "MULE_CART")   # the full menu
    assert item(cmd, "Double-Bit Axe") == "0:book:Double-Bit Axe:100 food · 50 wood · 25 s · research"
    assert item(cmd, "Gold Mining").startswith("1:book:Gold Mining:") and item(cmd, "Stone Mining").startswith("2:book:")
    assert len({s for s, _ in labels(cmd)}) == len(labels(cmd))   # one item per slot


def test_an_armenian_researches_double_bit_axe_and_gold_mining_at_the_mule_cart():
    server, g = setup()
    before = {r: g.work_time(r) for r in ("wood", "gold", "stone")}
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0) == 1 and train.order(g, "Steve", rect, 1) == 1
    assert (g.stock["food"], g.stock["wood"]) == (800, 875)
    for _ in range(60):
        train.tick(g, 1)                                               # one queue: 25 s, then 30 s
    assert {"DOUBLE_BIT_AXE", "GOLD_MINING"} <= g.techs and "STONE_MINING" not in g.techs
    assert g.work_time("wood") == pytest.approx(before["wood"] / 1.2)   # the same effect as at the camps
    assert g.work_time("gold") == pytest.approx(before["gold"] / 1.15) and g.work_time("stone") == before["stone"]


def test_the_lumber_and_mining_camp_menus_keep_their_slots():
    assert train.slots("LUMBER_CAMP", "DOUBLE_BIT_AXE")[0] == train.slots("MINING_CAMP", "GOLD_MINING")[0] == 0
    assert train.slots("MULE_CART", "GOLD_SHAFT_MINING")[0] == 1 and train.slots("MULE_CART", "STONE_SHAFT_MINING")[0] == 2
