"""game/gather.py: the sidebar names show the number of villagers on each resource, as "Wood (5)" (#5507). Only the
gather states count, and a name is sent only when its count changed."""
from test_idle import setup


def names(server):
    return [c for c in server.log if c.startswith("scoreboard players display name ") and " aoe_res " in c
            and "(" in c]


def test_the_names_show_the_workers_of_each_resource():
    server, g = setup()
    assert 'scoreboard players display name Wood aoe_res "Wood (0)"' in server.log
    g.villagers["a"].state, g.villagers["a"].res = "chop", "wood"
    g.villagers["b"].state, g.villagers["b"].res = "to_tree", "wood"
    g.villagers["c"].state, g.villagers["c"].res = "hunt", "food"
    g.workers()
    assert 'scoreboard players display name Wood aoe_res "Wood (2)"' in server.log
    assert 'scoreboard players display name Food aoe_res "Food (1)"' in server.log
    assert 'scoreboard players display name Gold aoe_res "Gold (0)"' in server.log


def test_no_command_when_no_count_changed():
    server, g = setup()
    g.villagers["a"].state, g.villagers["a"].res = "chop", "wood"
    g.workers()
    before = len(names(server))
    g.workers()
    assert len(names(server)) == before


def test_builders_and_idle_villagers_do_not_count():
    server, g = setup()
    site = {"name": "HOUSE", "player": 1, "footprint": [16, 18, 2, 4], "progress": 0.5}
    g.sites.append(site)
    for u, state in (("a", "build"), ("b", "idle"), ("c", "to_site")):
        g.villagers[u].state, g.villagers[u].res = state, "wood"
    g.workers()
    assert 'scoreboard players display name Wood aoe_res "Wood (0)"' in server.log   # set at the start, no change since
    assert not any(c.endswith('"Wood (1)"') or c.endswith('"Wood (2)"') or c.endswith('"Wood (3)"') for c in names(server))
