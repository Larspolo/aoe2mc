"""game/train.py and game/gather.py: the lumber camp menu has "Double-Bit Axe" (a book, 100 food and 50 wood, 25 AoE2
seconds). A click queues it once; after the research a villager chops one wood in 1/1.2 of the old time (#723)."""
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

from game import gather, train


def setup(food=100, wood=50):
    """A flat 16 × 16 map (tile size 1): a lumber camp of player 1 at blocks x 2-3, z 2-3 and a villager."""
    objects = [{"kind": "building", "name": "LUMBER_CAMP", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=food, wood=wood)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_lumber_camp_menu_has_double_bit_axe():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    assert menus(server) == ["aoe menu Steve Lumber Camp 0:book:Double-Bit Axe:100 food · 50 wood · 25 s · research"]


def test_a_click_queues_double_bit_axe_once_and_takes_its_cost():
    server, g = setup(food=500, wood=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == (400, 450)
    assert train.order(g, "Steve", rect, 0) == 0 and (g.stock["food"], g.stock["wood"]) == (400, 450)
    assert menus(server)[-1].endswith("0:book:Double-Bit Axe:100 food · 50 wood · 25 s · researching")


def test_not_enough_resources():
    server, g = setup(wood=49)
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is None and g.stock["wood"] == 49


def test_after_the_research_wood_is_20_percent_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in ("wood", "food", "farm", "gold", "stone")}
    train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE")
    train.tick(g, 24)
    assert not g.techs and g.work_time("wood") == before["wood"]
    train.tick(g, 1)
    assert g.techs == {"DOUBLE_BIT_AXE"} and not any(g.queues.values())
    assert g.work_time("wood") == pytest.approx(before["wood"] / 1.2)
    assert {r: g.work_time(r) for r in ("food", "farm", "gold", "stone")} == {r: before[r] for r in ("food", "farm", "gold", "stone")}
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    assert any("Double-Bit Axe is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Double-Bit Axe" not in menus(server)[-1]


def test_the_chop_step_uses_the_technology():
    """The chop state of Gather.step reads work_time: with the axe a villager gets 6 wood in 5.5 s, else 5."""
    loads = []
    for techs in (set(), {"DOUBLE_BIT_AXE"}):
        server, g = setup()
        g.techs = techs
        g.chop = dict.fromkeys(g.chop, 1.0)
        g.tick = 0.25
        v = next(iter(g.villagers.values()))
        v.state, v.res, v.tree, v.timer, v.load = "chop", "wood", (9, 9), 0.0, 0
        g.trunks[(9, 9)] = 0
        g.map.trees[(9, 9)] = 100
        for _ in range(22):                                            # 5.5 seconds
            g.step()
        loads.append(v.load)
    assert loads == [5, 6]
