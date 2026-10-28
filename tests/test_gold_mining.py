"""game/train.py and game/gather.py: the mining camp menu has "Gold Mining" (a book, 100 food and 75 wood, 30 AoE2
seconds). A click queues it once; after the research a villager mines one gold in 1/1.15 of the old time, and stone
does not change (#727)."""
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

from game import gather, train


def setup(food=100, wood=75, age=1):
    """A flat 16 × 16 map (tile size 1): a mining camp of player 1 at blocks x 2-3, z 2-3 and a villager."""
    objects = [{"kind": "building", "name": "MINING_CAMP", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=food, wood=wood)
    g.techs.update({"FEUDAL_AGE"} if age else ())                   # a Feudal Age technology (the key "age", #1046)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_mining_camp_menu_has_gold_mining():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    assert menus(server)[-1].startswith("aoe menu Steve Mining Camp 0:book:Gold Mining:100 food · 75 wood · 30 s · research ")


def test_a_click_queues_gold_mining_once_and_takes_its_cost():
    server, g = setup(food=500, wood=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, 0, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == (400, 425)
    assert train.order(g, "Steve", rect, 0) == 0 and (g.stock["food"], g.stock["wood"]) == (400, 425)
    assert " 0:book:Gold Mining:100 food · 75 wood · 30 s · researching " in menus(server)[-1] + " "


def test_after_the_research_gold_is_15_percent_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    train.queue(g, "Steve", (3, 3), "GOLD_MINING")
    train.tick(g, 29)
    assert g.techs == {"FEUDAL_AGE"} and g.work_time("gold") == before["gold"]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "GOLD_MINING"} and not any(g.queues.values())
    assert g.work_time("gold") == pytest.approx(before["gold"] / 1.15)
    assert {r: g.work_time(r) for r in gather.WORK_SECONDS if r != "gold"} == {r: t for r, t in before.items() if r != "gold"}
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    assert any("Gold Mining is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Gold Mining" not in menus(server)[-1]


def test_gold_mining_and_double_bit_axe_together():
    server, g = setup()
    base = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    g.techs.update({"GOLD_MINING", "DOUBLE_BIT_AXE"})
    assert g.work_time("gold") == pytest.approx(base["gold"] / 1.15)
    assert g.work_time("wood") == pytest.approx(base["wood"] / 1.2)
    assert g.work_time("stone") == base["stone"]
