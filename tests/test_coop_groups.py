"""game/gather.py: each Minecraft player of one AoE2 player has own control groups, as in AoE2 co-op (#3490, epic
#3485). Fake server: two names, "Alex" and "Steve", play player 1."""
import json

from test_coop_selection import pick, setup

from game import goto, savegame


def save(g, name, n):
    """Person name saves its selection as group n (shift + right click on the group item)."""
    g.person = name
    g.group(name, n, True)


def test_two_people_select_their_own_group_1():
    server, g = setup()
    pick(g, "Alex", {"v0", "v1"})
    save(g, "Alex", 1)
    pick(g, "Steve", {"m0"})
    save(g, "Steve", 1)
    pick(g, "Alex", set())
    pick(g, "Steve", set())
    g.person = "Alex"
    g.group("Alex", 1, False)
    g.person = "Steve"
    g.group("Steve", 1, False)
    assert g.selections["Alex"] == {"v0", "v1"} and g.selections["Steve"] == {"m0"}


def test_the_group_item_goes_only_to_its_person():
    server, g = setup()
    pick(g, "Steve", {"m0"})
    server.log.clear()
    save(g, "Steve", 1)
    give = [c for c in server.log if c.startswith("item replace")]
    assert give and all(c.split()[3] == "Steve" for c in give) and 'Group 1: 1 unit"' in give[0]


def test_the_go_to_menu_shows_the_groups_of_its_person():
    server, g = setup()
    pick(g, "Alex", {"v0", "v1"})
    save(g, "Alex", 1)
    g.person = "Steve"
    assert "Group 1: 0 units" in [i[2] for i in goto.items(g)]
    g.person = "Alex"
    assert "Group 1: 2 units" in [i[2] for i in goto.items(g)]


def test_a_saved_game_keeps_the_groups_of_each_person():
    server, g = setup()
    pick(g, "Alex", {"v0", "v1"})
    save(g, "Alex", 1)
    pick(g, "Steve", {"m0"})
    save(g, "Steve", 2)
    p = json.loads(json.dumps(savegame.orders(g)))
    _, h = setup()
    savegame.give_orders(h, p)
    assert h.person_groups == {"Alex": {1: {"v0", "v1"}}, "Steve": {2: {"m0"}}}


def test_an_old_save_gives_its_groups_to_the_first_person():
    _, g = setup()
    p = json.loads(json.dumps(savegame.orders(g)))
    p["groups"] = {"3": ["m1"]}                                         # one group set for all (before #3490)
    savegame.give_orders(g, p)
    g.person = "Alex"
    assert g.groups == {3: {"m1"}}
