"""game/gather.py: a click with selected units that cannot gather (a scout) on a resource or a construction site
gives no error; the villagers of the selection still go (#589)."""
from test_gather import FakeServer, grid
from test_gather_farms import FARMS

from game import gather


def setup():
    """A flat 24 × 24 map (tile size 1): a town center, a mill, two farms, a tree, a villager and a scout."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "MILL", "player": 1, "tile": [13, 15], "footprint": [12, 14, 14, 16]},
               {"kind": "other", "name": "TREE_OAK", "tile": [20.5, 4.5]}]
    objects += [{"kind": "building", "name": "FARM", "player": 1, "tile": [t[0] + 0.5, t[1] + 0.5], "footprint": f}
                for t, f in FARMS.items()]
    objects += [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [7.5, z]}
                for u, n, z in (("v", "VILLAGER_MALE", 7.5), ("scout", "SCOUT_CAVALRY", 8.5))]
    server = FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}, "scout": {"Pos": (7.5, 64.0, 8.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.selected = {"v", "scout"}
    return g


def test_a_scout_in_the_selection_does_not_stop_a_send_to_a_tree_or_a_farm():
    for tile, state in (((20, 4), "to_tree"), ((10, 10), "to_tree")):
        g = setup()
        assert "scout" in g.soldiers and set(g.villagers) == {"v"}
        g.send(tile)
        assert g.villagers["v"].tree == tile and g.villagers["v"].state == state
        assert "scout" not in g.farmers.values()


def test_a_scout_in_the_selection_does_not_stop_a_build():
    g = setup()
    site = {"footprint": [9, 11, 18, 20], "progress": 0}
    g.build(site)
    assert g.villagers["v"].site is site and g.villagers["v"].state == "to_site"
