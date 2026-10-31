"""The object search of an AI script (direct unit control, #4957): up-find-local, up-find-remote, the search state, the
resets, up-clean-search and the target object, with the airef examples. The map of test_bot_gather: the bot (player 2)
has a town center and five villagers, player 1 (the enemy) a town center and the villager p1."""
from test_bot_gather import bot_map
from test_per_save import game, scripted

from game import per, savegame
from game.bot import build, train  # noqa: F401  the modules that per uses


def script(text=""):
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    b.g.soldiers.update(m1="MILITIA", m2="SPEARMAN", k1="KNIGHT")
    return per.Script(per.parse(text), b), b, me


def run(s, text):
    """Run the actions of one rule (true) on the script."""
    for a in per.parse(f"(defrule (true) => {text})")[0].actions:
        s.act(0, a)


def state(s):
    run(s, "(up-get-search-state 100)")
    return [s.goals[100 + i] for i in range(4)]                         # local total, last; remote total, last


def test_find_local_goes_on_resets_and_sets_the_target():
    s, b, me = script()
    run(s, "(up-find-local c: infantry-class c: 20)")                   # airef: infantry-class = 906
    assert state(s) == [2, 2, 0, 0]
    assert s.search[1]["found"] == [s.ids["m1"], s.ids["m2"]]
    run(s, "(up-find-local c: infantry-class c: 20)")                   # the scan goes on: nothing more
    assert state(s) == [2, 0, 0, 0]
    assert not s.check(("up-can-search", "search-local"))               # the scan is at the end of the objects
    s.rules = per.parse("(defrule (not (up-can-search search-local)) => (up-reset-search 1 1 0 0))")
    s.step()
    assert state(s) == [0, 0, 0, 0] and s.check(("up-can-search", "search-local"))
    run(s, "(up-find-local c: 906 c: 1)")                               # an id; one at a time
    run(s, "(up-find-local c: 906 c: 1)")
    assert s.search[1]["found"] == [s.ids["m1"], s.ids["m2"]]
    run(s, "(up-find-local c: villager-class c: 3) (up-set-target-object search-local c: 0)")   # another type: from 0
    villagers = [s.ids[u] for u in b.g.villagers][:3]
    assert s.search[1]["found"][2:] == villagers and s.target == s.search[1]["found"][0]
    assert not s.check(("up-set-target-object", "search-local", "c:", 9))   # an invalid index keeps the target
    assert s.target == s.ids["m1"] and not s.warned


def test_find_remote_finds_only_the_seen_objects_of_the_focus_player():
    s, b, me = script()
    me.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 1, "footprint": [8, 8, 12, 12]})
    run(s, "(set-strategic-number sn-focus-player-number 2) (up-find-remote c: castle c: 4)")
    assert state(s) == [0, 0, 0, 0]                                     # the bot has no castle
    run(s, "(set-strategic-number sn-focus-player-number 1) (up-find-remote c: castle c: 4)")   # airef: focus 2
    assert state(s)[2:] == [1, 1] and s.check(("up-find-remote", "c:", "villager-class", "c:", 5))
    b.g.fog = {"hidden": {"p1"}}                                        # the villager went out of sight
    run(s, "(up-reset-search 0 0 1 1) (up-find-remote c: villager-class c: 5)")
    assert state(s)[2:] == [0, 0]
    assert s.check(("up-find-remote", "c:", "castle", "c:", 4))         # a building stays found in the fog
    assert not s.check(("up-find-local", "c:", "no-such-class", "c:", 4)) and s.warned == {("unit or building", "no-such-class")}


def test_add_by_id_clean_search_and_target_by_id():
    s, b, me = script()
    run(s, "(up-find-local c: militiaman c: 5)")
    s.goals[100] = s.ids["k1"]                                          # airef: gl-stored-id 100
    run(s, "(up-add-object-by-id search-local g: 100) (up-add-object-by-id search-local g: 100)")
    assert s.search[1]["found"] == [s.ids["m1"], s.ids["k1"], s.ids["k1"]]
    run(s, "(up-clean-search search-local -1 search-order-desc)")
    assert s.search[1]["found"] == [s.ids["k1"], s.ids["m1"]]
    run(s, "(up-clean-search search-local -1 search-order-asc)")
    assert s.search[1]["found"] == [s.ids["m1"], s.ids["k1"]]
    run(s, "(up-set-target-by-id g: 100)")
    assert s.target == s.ids["k1"]
    s.goals[100] = 999
    assert not s.check(("up-set-target-by-id", "g:", 100)) and s.target == s.ids["k1"]   # no such id: no change
    assert not s.check(("up-add-object-by-id", "search-remote", "g:", 100))
    s.filters["test"] = 1
    run(s, "(up-reset-filters)")
    assert s.filters == {} and s.search[1]["after"] == 0 and len(s.search[1]["found"]) == 2
    run(s, "(up-full-reset-search)")
    assert state(s) == [0, 0, 0, 0] and not s.warned


def test_an_id_stays_when_another_object_dies_and_a_new_object_gets_a_new_id():
    s, b, me = script()
    run(s, "(up-find-local c: villager c: 10)")
    before = dict(s.ids)
    del b.g.villagers[next(iter(b.g.villagers))]                       # a villager dies
    b.g.soldiers["m3"] = "MILITIA"                                     # a new soldier
    s.objects(b.g)
    assert {k: s.ids[k] for k in before} == before and s.ids["m3"] == max(before.values()) + 1


def test_a_load_keeps_the_ids_the_search_and_the_target():
    me = scripted(game(("standard",) * 3, (1, 1, 1)))
    s = me.bots[0].script
    run(s, "(up-find-local c: town-center c: 2) (up-set-target-object search-local c: 0)")   # its town center
    new = scripted(game(("standard",) * 3, (1, 1, 1)))
    savegame.load(new, savegame.dump(me))
    t = new.bots[0].script
    assert (t.ids, t.next_id, t.search, t.target) == (s.ids, s.next_id, s.search, s.target) and t.target is not None
