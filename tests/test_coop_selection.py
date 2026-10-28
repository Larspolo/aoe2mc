"""game/gather.py: each Minecraft player of one AoE2 player has an own selection and gives own orders, as in AoE2
co-op (#3486, epic #3485). Fake server: two names, "Alex" and "Steve", play player 1."""
import re

from test_gather import FakeServer, grid

from game import gather

LOOK = {"Pos": (8.5, 64.0, 12.5), "Rotation": (-90.0, 30.0)}   # looks east and down at the ground near x = 10


def setup():
    """A flat 24 × 24 map (tile size 1): militia "m0", "m1", villagers "v0", "v1", a tree at (15, 4), a gold mine at
    (4, 15)."""
    objects = [{"kind": "unit", "name": "MILITIA", "player": 1, "uuid": f"m{k}", "tile": [4.5 + k, 18.5]} for k in range(2)]
    objects += [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [4.5 + k, 20.5]}
                for k in range(2)]
    ents = {o["uuid"]: {"Pos": (o["tile"][0], 64.0, o["tile"][1])} for o in objects} | {"Alex": dict(LOOK), "Steve": dict(LOOK)}
    objects += [{"kind": "other", "name": "TREE_OAK", "tile": [15.5, 4.5]}, {"kind": "other", "name": "GOLD_MINE", "tile": [4.5, 15.5]}]
    server = FakeServer(ents)
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    return server, g


def pick(g, name, units):
    """Person name selects units, as its box selection does."""
    g.person = name
    g.choose(set(units), min(units, default=None))


def moved(server):
    """The units of the `aoe moveto` commands in the log."""
    return {m[1] for c in server.log if (m := re.match(r"aoe moveto (\S+) ", c))}


def test_two_people_of_one_player_order_their_own_units():
    server, g = setup()
    pick(g, "Alex", {"m0"})
    pick(g, "Steve", {"m1"})
    server.log.clear()
    g.click("Alex")
    assert moved(server) == {"m0"}
    server.log.clear()
    g.click("Steve")
    assert moved(server) == {"m1"}
    assert g.selections["Alex"] == {"m0"} and g.selections["Steve"] == {"m1"}


def test_the_villagers_of_two_people_go_to_their_own_resources():
    server, g = setup()
    tree, mine = (15, 4), (4, 15)
    pick(g, "Alex", {"v0"})
    g.send(tree)
    pick(g, "Steve", {"v1"})
    g.send(mine)
    assert (g.villagers["v0"].tree, g.villagers["v0"].res) == (tree, "wood")
    assert (g.villagers["v1"].tree, g.villagers["v1"].res) == (mine, "gold")


def test_a_click_of_a_person_with_no_selection_moves_no_unit_of_the_other():
    server, g = setup()
    pick(g, "Alex", {"m0", "m1"})
    server.log.clear()
    g.click("Steve")
    assert moved(server) == set()
    assert g.selections["Alex"] == {"m0", "m1"}


def test_a_unit_keeps_its_glow_while_another_person_has_it_selected():
    server, g = setup()
    pick(g, "Alex", {"m0"})
    pick(g, "Steve", {"m0"})
    server.log.clear()
    pick(g, "Alex", set())
    assert "data merge entity m0 {Glowing:0b}" not in server.log
    pick(g, "Steve", set())
    assert "data merge entity m0 {Glowing:0b}" in server.log


def test_a_dead_unit_leaves_the_selection_of_each_person():
    server, g = setup()
    pick(g, "Alex", {"m0", "m1"})
    pick(g, "Steve", {"m0"})
    g.drop("m0")
    assert g.selections["Alex"] == {"m1"} and g.selections["Steve"] == set()


def test_the_first_person_who_clicks_takes_a_selection_with_no_person():
    server, g = setup()
    g.selected = {"m0"}                                                # a setup: no click, no person
    server.log.clear()
    g.click("Steve")
    assert moved(server) == {"m0"}
    g.click("Alex")
    assert g.selections == {"Steve": {"m0"}, "Alex": set()}
