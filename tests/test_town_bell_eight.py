"""The town bell with 8 villagers at work and a mule cart at one town center: all go inside, and "All Back to Work"
sends each villager back to its old work (#3413, #3420)."""
from test_garrison_game import TC, setup
from test_town_bell_back import click, inside

WORK = {"v0": (20, 15), "v1": (21, 15), "v2": (22, 15), "v3": (15, 20), "v4": (16, 20),
        "v5": (12, 20), "v6": (18, 18), "v7": (21, 21)}
RES = dict(zip(WORK, ["wood"] * 3 + ["gold"] * 2 + ["stone"] + ["food"] * 2))


def test_bell_and_all_back_to_work_with_eight_workers_and_a_mule_cart():
    server, g = setup(villagers=8)
    g.data["objects"] = [o for o in g.data["objects"] if o["name"] != "WATCH_TOWER"]   # the town center is the only holder
    for tile in set(WORK.values()):
        if tile in {(18, 18), (21, 21)}:
            g.map.farms[tile] = 175
        elif tile in {(15, 20), (16, 20), (12, 20)}:
            g.map.mines["gold" if tile != (12, 20) else "stone"][tile] = 800
        else:
            g.map.trees[tile] = 100
        g.map.feet[tile] = (tile[0], tile[0] + 1, tile[1], tile[1] + 1)
    for k, (u, tile) in enumerate(WORK.items()):
        g.send(tile, {u})
        server.entities[u]["Pos"] = (5.5 + k / 2, 64.0, 7.5)       # within the sight of the town center (8 tiles)
    g.soldiers["c0"] = "MULE_CART"
    server.entities["c0"] = {"Pos": (5.5, 64.0, 9.5)}
    click(g)
    assert set(g.entering) == set(WORK) | {"c0"} and set(g.entering.values()) == {TC}
    inside(server, g)
    assert sorted(g.garrisons[TC]) == sorted(list(WORK) + ["c0"])
    click(g)
    assert not g.garrisons and not g.bell_work
    for u, tile in WORK.items():
        assert (g.villagers[u].tree, g.villagers[u].res) == (tile, RES[u]) and g.villagers[u].state == "to_tree", u
