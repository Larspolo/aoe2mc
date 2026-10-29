"""A villager fells a tree after an own building fell (#4147): ruins.fall kept the lost buildings in g.fell, which hid
the method Gather.fell, and the next felled tree stopped the game with "'list' object is not callable"."""
from test_build_on_stump import TREE, game
from test_delete_loss import HOUSE, town

from game import demolish, savegame


def test_a_tree_falls_after_a_building_fell():
    _, g = town()
    assert demolish.delete(g, "Steve", HOUSE)
    assert g.buildings_lost and callable(g.fell)
    _, g = game()
    g.buildings_lost = [("HOUSE", False)]
    g.fell(TREE)                                                       # no TypeError


def test_a_save_with_the_old_key_loads_the_lost_buildings():
    _, g = town()
    p = savegame.dump(g)["players"]["1"]
    p["fell"] = p.pop("buildings_lost", [["HOUSE", False]])
    savegame.fields_again(g, p)
    assert callable(g.fell) and list(map(tuple, g.buildings_lost)) == [("HOUSE", False)]
