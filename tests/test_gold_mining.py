"""game/train.py and game/gather.py: the mining camp menu has "Gold Mining" (a book). A click queues it once; after
the research a villager mines gold faster, and stone does not change (#727)."""
from urllib.parse import unquote

from menu_line import item
from test_gather import FakeServer, grid

from game import gather, train


def setup(food=1000, wood=1000, age=1):
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
    assert menus(server)[-1].startswith("aoe menu Steve Mining Camp ")
    assert item(menus(server)[-1], "Gold Mining").endswith(" · research")


def test_a_click_queues_gold_mining_once_and_takes_its_cost():
    server, g = setup(food=500, wood=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    cost, slot = train.price(g, "GOLD_MINING"), train.SLOTS["GOLD_MINING"]
    left = (500 - cost.get("food", 0), 500 - cost.get("wood", 0))
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == left
    assert train.order(g, "Steve", rect, slot) == 0 and (g.stock["food"], g.stock["wood"]) == left
    assert item(menus(server)[-1], "Gold Mining").endswith(" · researching")


def test_after_the_research_gold_is_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    train.queue(g, "Steve", (3, 3), "GOLD_MINING")
    train.tick(g, train.seconds(g, "GOLD_MINING", "MINING_CAMP") - 1)
    assert g.techs == {"FEUDAL_AGE"} and g.work_time("gold") == before["gold"]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "GOLD_MINING"} and not any(g.queues.values())
    assert g.work_time("gold") < before["gold"]
    assert {r: g.work_time(r) for r in gather.WORK_SECONDS if r != "gold"} == {r: t for r, t in before.items() if r != "gold"}
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    assert any("Gold Mining is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Gold Mining" not in menus(server)[-1]


def test_gold_mining_and_double_bit_axe_together():
    server, g = setup()
    base = {r: g.work_time(r) for r in gather.WORK_SECONDS}
    g.techs.update({"GOLD_MINING", "DOUBLE_BIT_AXE"})
    assert g.work_time("gold") < base["gold"] and g.work_time("wood") < base["wood"]
    assert g.work_time("stone") == base["stone"]
