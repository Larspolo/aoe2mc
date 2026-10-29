"""After the town bell, "All Back to Work" and "Ungarrison" send each villager of the bell back to its old work, as
in AoE2 DE (#3420)."""
import json

from menu_line import item
from test_garrison_game import TC, arrive, setup
from test_train_menu import menus

from game import garrison, savegame, train

TREE, GOLD, FARM, FARM2 = (20, 15), (15, 20), (18, 18), (21, 21)


def working(villagers=3):
    """The setup of the bell tests: v0 chops a tree, v1 mines gold, v2 farms; a far villager v3 stays outside."""
    server, g = setup(villagers=villagers)
    g.map.trees[TREE] = 100
    g.map.mines["gold"][GOLD] = 800
    g.map.farms[FARM] = g.map.farms[FARM2] = 175
    for x, z in (GOLD, FARM, FARM2):                               # the footprints of the mine and the farms
        g.map.feet[(x, z)] = (x, x + 1, z, z + 1)
    for u, tile in (("v0", TREE), ("v1", GOLD), ("v2", FARM))[:villagers]:
        g.send(tile, {u})
    return server, g


def click(g, slot=garrison.BELL[0]):
    train.open_menu(g, "Steve", (3, 3))
    train.order(g, "Steve", TC, slot)


def inside(server, g):
    for rect in set(g.entering.values()):
        arrive(server, g, rect)


def test_all_back_to_work_sends_each_villager_to_its_old_work_and_a_taken_farm_stays():
    server, g = working(villagers=4)
    server.entities["v3"]["Pos"] = (22.5, 64.0, 22.5)              # far from the buildings: it does not go inside
    click(g)
    assert set(g.bell_work) == {"v0", "v1", "v2"}
    inside(server, g)
    assert sorted(u for us in g.garrisons.values() for u in us) == ["v0", "v1", "v2"]
    g.send(FARM, {"v3"})                                           # another farmer takes the farm of v2
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "All Back to Work").startswith("24:bell:All Back to Work")
    click(g)
    assert not g.garrisons and not g.bell_work
    assert (g.villagers["v0"].tree, g.villagers["v0"].res) == (TREE, "wood")
    assert (g.villagers["v1"].tree, g.villagers["v1"].res) == (GOLD, "gold")
    assert g.villagers["v2"].tree == FARM2 and g.farmers[FARM] == "v3" and g.farmers[FARM2] == "v2"
    assert all(g.villagers[u].state == "to_tree" for u in ("v0", "v1", "v2"))
    train.open_menu(g, "Steve", (3, 3))
    assert item(menus(server)[-1], "Ring Town Bell")


def test_ungarrison_of_the_town_center_sends_a_villager_of_the_bell_back_to_work():
    server, g = working(villagers=1)
    click(g)
    inside(server, g)
    rect = next(r for r, us in g.garrisons.items() if "v0" in us)
    assert rect == TC
    click(g, garrison.ungarrison("TOWN_CENTER")[0])
    assert g.villagers["v0"].tree == TREE and g.villagers["v0"].state == "to_tree" and not g.bell_work


def test_a_save_keeps_the_work_of_the_bell():
    server, g = working()
    click(g)
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.bell_work == g.bell_work == {"v0": ("tile", TREE), "v1": ("tile", GOLD), "v2": ("tile", FARM)}
