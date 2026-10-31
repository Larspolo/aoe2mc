"""The filters of the object search of an AI script (#4958): up-filter-include, -exclude, -distance, -range, -garrison,
-status, up-find-status-local, -remote and up-find-resource, with the airef examples. The map of test_bot_gather: the
bot (player 2) has a town center at tiles 20-23 and five villagers at (24.5, 19.5 + i); player 1 a villager."""
from test_per_up_search import run, script, state


def found(s, text, reset="(up-reset-search 1 1 1 1)"):
    """The count of objects in the local and the remote list after the actions text (the filters stay)."""
    run(s, reset + text)
    return state(s)[0], state(s)[2]


def test_include_and_exclude_select_by_the_command_id():
    s, b, me = script()
    assert found(s, "(up-find-local c: villager-class c: 20)") == (5, 0)
    assert found(s, "(up-filter-include 3 -1 -1 -1) (up-find-local c: villager-class c: 20)") == (5, 0)   # airef
    assert found(s, "(up-find-local c: infantry-class c: 20)") == (0, 0)
    run(s, "(up-reset-filters)")
    assert found(s, "(up-filter-exclude 3 -1 -1 -1) (up-find-local c: villager-class c: 20)") == (0, 0)
    assert found(s, "(up-find-local c: infantry-class c: 20)") == (2, 0)
    assert not s.warned
    run(s, "(up-reset-filters) (up-filter-exclude 5 -1 -1 -1)")         # airef: trade units, not in the game program
    assert s.warned == {("command id", 5)} and found(s, "(up-find-local c: villager-class c: 20)") == (5, 0)


def test_distance_and_range_count_tiles_from_the_target_point():
    s, b, me = script()
    s.goals.update({50: 24, 51: 19})
    run(s, "(up-set-target-point 50)")
    assert found(s, "(up-filter-distance c: -1 c: 10) (up-find-local c: villager-class c: 20)") == (5, 0)   # airef
    assert found(s, "(up-filter-distance c: -1 c: 2) (up-find-local c: villager-class c: 20)") == (2, 0)
    assert found(s, "(up-filter-distance c: 2 c: -1) (up-find-local c: villager-class c: 20)") == (3, 0)
    run(s, "(up-reset-filters)")
    assert found(s, "(up-filter-range -1 -1 -1 2) (up-find-local c: villager-class c: 20)") == (2, 0)
    assert found(s, "(up-filter-range -1 -1 -1 10) (up-find-local c: villager-class c: 20)") == (5, 0)   # airef


def test_garrison_counts_the_units_inside():
    s, b, me = script()
    assert found(s, "(up-filter-garrison c: 5 c: -1) (up-find-local c: town-center c: 5)") == (0, 0)   # airef
    b.g.garrisons[(20, 23, 20, 23)] = [f"b{i}" for i in range(5)]
    assert found(s, "(up-find-local c: town-center c: 5)") == (1, 0)
    assert found(s, "(up-filter-range 0 4 -1 -1) (up-find-local c: town-center c: 5)") == (0, 0)


def test_status_finds_sites_fallen_buildings_and_remote_objects():
    s, b, me = script()
    b.g.sites.append({"name": "CASTLE", "player": 2, "footprint": (8, 12, 8, 12), "progress": 0.2, "done": False})
    assert found(s, "(up-find-local c: castle c: 5)") == (0, 0)
    assert found(s, "(up-filter-status c: status-pending c: list-active) (up-find-status-local c: castle c: 5)") == \
        (1, 0)                                                         # airef: only incomplete castles
    assert found(s, "(up-filter-status c: status-ready c: list-active) (up-find-status-local c: town-center c: 5)") \
        == (1, 0)
    b.g.ruins = {(20, 23, 20, 23)}                                     # the town center fell
    assert found(s, "(up-find-status-local c: town-center c: 5)") == (0, 0)
    assert found(s, "(up-filter-status c: status-down c: list-active) (up-find-status-local c: town-center c: 5)") == \
        (1, 0)
    run(s, "(set-strategic-number sn-focus-player-number 1)")
    assert found(s, "(up-filter-status c: status-ready c: list-active) (up-find-status-remote c: villager-class c: 5)") \
        == (0, 1)
    assert not s.warned


def test_find_resource_finds_the_seen_resources_of_the_status():
    s, b, me = script()
    assert found(s, "(up-find-resource c: gold c: 2)") == (0, 0)       # gold has status-resource
    assert found(s, "(up-filter-status c: status-resource c: list-active) (up-find-resource c: gold c: 2)") == (0, 1)
    assert found(s, "(up-find-resource c: 0 c: 5)") == (0, 1)          # food (an id): the fruit bush
    assert found(s, "(up-filter-status c: status-ready c: list-active) (up-find-resource c: wood c: 1)") == (0, 1)
    assert s.check(("up-find-resource", "c:", "wood", "c:", 5)) and state(s)[2:] == [2, 1]   # the scan goes on
    run(s, "(up-set-target-object search-remote c: 0)")
    assert s.target == s.search[2]["found"][0]
    assert not s.check(("up-find-resource", "c:", "boar", "c:", 1)) and s.warned == {("resource", "boar")}
