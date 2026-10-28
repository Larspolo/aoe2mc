"""game/train.py: the menu item "Rally point" and the next right click on the ground set the rally point of a building;
a new villager walks there or gathers at the resource there, a new military unit walks there (#707)."""
from test_train import setup

from game import train

TC = (2, 5, 2, 5)                                                      # the footprint of the own town center


def test_the_menu_item_and_a_right_click_on_the_ground_set_the_rally_point():
    server, g = setup()
    for name in g.clicks():
        g.click(name)                                                  # opens the menu of the town center
    server.scores["aoe_menu"] = train.RALLY[0] + 1                      # a click on the rally item
    g.clicks()
    assert g.rallying == {"Steve": TC} and "aoe menu-close Steve" in server.log and "Steve" not in g.menus
    server.entities["Steve"]["Rotation"] = (0, 60)                     # looks down, south: the ground at (3, 10)
    server.scores["aoe_use"] = 1
    for name in g.clicks():
        g.click(name)
    assert g.rally == {TC: ((3, 10), None)} and not g.rallying and not any(g.queues.values())
    marks = [c for c in server.log if c.startswith("summon") and "aoe2mc.rally.2.2" in c]
    assert [c.split()[1] for c in marks] == ["item_display", "text_display"] and "Rally point" in marks[1]
    train.tick(g, train.MARK)
    assert server.log[-1] == "kill @e[tag=aoe2mc.rally.2.2]" and not g.marks


def test_a_new_villager_walks_to_the_rally_point():
    server, g = setup()
    train.rally(g, TC, (12, 14))
    train.queue(g, "Steve", (3, 3))
    v = train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])[0]
    assert v.state == "to_rally" and v.path[-1] == (12, 14)
    server.entities[v.uuid] = {"Pos": v.pos}                           # the server knows the new villager
    for _ in range(40):
        g.step()
    assert v.state == "idle" and v.cell == (12, 14)


def test_a_new_villager_gathers_at_a_rally_point_on_a_tree():
    server, g = setup()
    train.rally(g, TC, (20, 4), (20, 4))
    train.queue(g, "Steve", (3, 3))
    v = train.tick(g, train.TRAIN_TIMES["VILLAGER_MALE"])[0]
    assert v.state == "to_tree" and v.tree == (20, 4) and v.res == "wood"


def test_a_new_military_unit_walks_to_the_rally_point_with_the_plugin():
    server, g = setup()
    train.rally(g, TC, (10, 12))
    train.go(g, TC, "m", "MILITIA")
    assert "aoe moveto m 10.5 64 12.5" in server.log


def test_a_building_without_units_has_no_rally_point():
    _, g = setup()
    assert train.units_of(g, "BLACKSMITH") == [] and train.units_of(g, "TOWN_CENTER") == ["VILLAGER_MALE"]
