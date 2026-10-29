"""game/train.py and game/gather.py: the lumber camp menu has "Double-Bit Axe" from the Feudal Age (#760). A click
queues it once; after the research a villager chops wood faster (#723)."""
from urllib.parse import unquote

from menu_line import item, labels, order
from test_gather import FakeServer, grid

from game import gather, train


TECH = "DOUBLE_BIT_AXE"
COST, TIME = train.COSTS[TECH], train.TRAIN_TIMES[TECH]


def line(state):
    """The menu item of the technology with its cost and time."""
    slot, icon, label = train.ITEMS[TECH]
    return f"{slot}:{icon}:{label}:" + " · ".join([f"{v} {k}" for k, v in COST.items()] + [f"{TIME} s", state])


def setup(food=COST.get("food", 0), wood=COST.get("wood", 0)):
    """A flat 16 × 16 map (tile size 1): a lumber camp of player 1 at blocks x 2-3, z 2-3 and a villager."""
    objects = [{"kind": "building", "name": "LUMBER_CAMP", "player": 1, "tile": [3.0, 3.0], "footprint": [2, 2, 4, 4]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.stock.update(food=food, wood=wood)
    g.techs.add("FEUDAL_AGE")                                          # a Feudal Age technology (#760)
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_the_lumber_camp_menu_has_double_bit_axe():
    server, g = setup()
    assert train.open_menu(g, "Steve", (2, 3)) == (2, 4, 2, 4)
    cmd, = menus(server)
    assert cmd.startswith("aoe menu Steve Lumber Camp ") and labels(cmd) == order(g, "LUMBER_CAMP")   # the full menu
    assert item(cmd, "Double-Bit Axe") == line("research")


def test_no_double_bit_axe_in_the_dark_age():
    server, g = setup()
    g.techs.clear()
    train.open_menu(g, "Steve", (3, 3))
    assert "Double-Bit Axe" not in menus(server)[-1] and train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is None
    assert (g.stock["food"], g.stock["wood"]) == (COST.get("food", 0), COST.get("wood", 0))


def test_a_click_queues_double_bit_axe_once_and_takes_its_cost():
    server, g = setup(food=500, wood=500)
    rect = train.open_menu(g, "Steve", (3, 3))
    left = (500 - COST.get("food", 0), 500 - COST.get("wood", 0))
    slot = train.ITEMS[TECH][0]
    assert train.order(g, "Steve", rect, slot, shift=True) == 1 and (g.stock["food"], g.stock["wood"]) == left
    assert train.order(g, "Steve", rect, slot) == 0 and (g.stock["food"], g.stock["wood"]) == left
    assert item(menus(server)[-1], "Double-Bit Axe") == line("researching")


def test_not_enough_resources():
    server, g = setup(wood=COST["wood"] - 1)
    assert train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE") is None and g.stock["wood"] == COST["wood"] - 1


def test_after_the_research_wood_is_faster():
    server, g = setup()
    before = {r: g.work_time(r) for r in ("wood", "food", "farm", "gold", "stone")}
    train.queue(g, "Steve", (3, 3), "DOUBLE_BIT_AXE")
    train.tick(g, TIME - 1)
    assert g.techs == {"FEUDAL_AGE"} and g.work_time("wood") == before["wood"]
    train.tick(g, 1)
    assert g.techs == {"FEUDAL_AGE", "DOUBLE_BIT_AXE"} and not any(g.queues.values())
    assert g.work_time("wood") < before["wood"]
    assert {r: g.work_time(r) for r in ("food", "farm", "gold", "stone")} == {r: before[r] for r in ("food", "farm", "gold", "stone")}
    assert not [c for c in server.log if c.startswith("aoe stats")]   # no combat change
    assert any("Double-Bit Axe is researched." in c for c in server.log if c.startswith("tellraw"))
    train.open_menu(g, "Steve", (3, 3))
    assert "Double-Bit Axe" not in menus(server)[-1]


def test_the_chop_step_uses_the_technology():
    """The chop state of Gather.step reads work_time: with the axe a villager gets more wood in 5.5 s."""
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
    assert 0 < loads[0] < loads[1]
