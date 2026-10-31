"""The search groups of an AI script (#4961): up-create-group, up-set-group, up-reset-group, up-get-group-size,
up-group-size, up-modify-group-flag and up-disband-group-type, with the airef examples. The map of test_bot_gather (as
test_per_up_search): the bot has five villagers and the soldiers m1, m2 and k1."""
from test_per_up_search import run, script


def size(s, gid):
    run(s, f"(up-get-group-size c: {gid} 100)")                         # airef: (up-get-group-size c: 0 gl-size)
    return s.goals[100]


def test_create_set_reset_and_a_dead_unit():
    s, b, me = script()
    s.goals.update({1: 0, 2: 3})                                        # the index goal, the count goal
    run(s, "(up-reset-search 1 1 1 1) (up-reset-filters) (up-find-local c: villager-class c: 10)"
           " (up-create-group 0 0 c: 0)")                               # airef: up to 10 villagers, count 0 = 40
    villagers = s.search[1]["found"][:]
    assert size(s, 0) == len(villagers) == 5
    assert s.check(("up-group-size", "c:", 0, ">", 0)) and not s.check(("up-group-size", "c:", 1, ">", 0))
    run(s, "(up-create-group 1 2 c: 1)")                                # 3 from index 0
    assert s.groups[1] == villagers[:3]
    s.goals[1] = 4
    run(s, "(up-create-group 1 2 c: 1)")                                # from index 4: only 1 left; reset first
    assert s.groups[1] == villagers[4:]
    run(s, "(up-full-reset-search) (up-set-group search-local c: 0)")    # airef: the group into the local results
    assert s.search[1]["found"] == villagers
    del b.g.villagers[next(u for u, i in s.ids.items() if i == villagers[0])]   # a villager dies
    assert size(s, 0) == 4 and villagers[0] not in s.groups[0]
    run(s, "(up-reset-group c: 0)")                                     # airef: reset the first search group
    assert size(s, 0) == 0 and not s.check(("up-group-size", "c:", 0, ">", 0))
    run(s, "(up-full-reset-search) (up-create-group 0 0 c: 2)")         # no results: the group is cleared
    assert size(s, 2) == 0 and not s.warned


def test_group_flag_and_a_bad_group():
    s, b, me = script()
    run(s, "(up-find-local c: infantry-class c: 20) (up-create-group 0 0 c: 2) (up-modify-group-flag 1 c: 2)")
    assert s.flags == {s.ids["m1"]: 2, s.ids["m2"]: 2}                  # airef: object-data-group-flag will be 2
    del b.g.soldiers["m2"]
    run(s, "(up-get-group-size c: 2 100) (up-modify-group-flag 0 c: 2)")
    assert s.goals[100] == 1 and s.flags == {}
    run(s, "(up-reset-group c: 20)")
    assert s.warned == {("group", 20)}


def test_disband_group_types():
    s, b, me = script()
    b.wave, b.targets = {"m1", "m2"}, {"m1": "p1"}
    s.scouts = ["k1"]
    sent = []
    command = b.g.command
    b.g.command = lambda c: sent.append(c) or command(c)
    run(s, "(up-disband-group-type group-type-land-attack)")
    assert b.wave == set() and b.targets == {} and {"aoe stop m1", "aoe stop m2"} <= set(sent)
    run(s, "(up-disband-group-type group-type-land-explore)")           # airef: stop the land explore groups
    assert s.scouts == [] and "aoe stop k1" in sent
    run(s, "(up-disband-group-type group-type-monk) (up-disband-group-type group-type-monk)")
    assert s.warned == {("group type", "group-type-monk")}              # one warning
