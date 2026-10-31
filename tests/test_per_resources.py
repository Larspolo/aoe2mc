"""game/per.py: an AI script reads the resources that its bot found and their distance (#4739). The map of
test_bot_gather."""
from test_bot_gather import bot_map

from game import per


def script():
    server, me, b = bot_map()
    return per.Script(per.parse("(defrule (true) => (disable-self))"), b), b


def test_resource_found_reads_the_own_mines():
    s, b = script()
    assert s.check(("resource-found", "gold"))
    b.g.map.mines["gold"] = {}
    assert not s.check(("resource-found", "gold"))


def test_a_lumber_camp_next_to_the_trees_makes_the_distance_small():
    s, b = script()
    m = b.g.map
    m.trees = {(29, 10): 100}                                          # far from the town center, on the own side
    assert not s.check(("dropsite-min-distance", "wood", "<", 6))
    m.drop_site("LUMBER_CAMP", {(x, z) for x in (27, 28) for z in (10, 11)})
    assert s.check(("dropsite-min-distance", "wood", "<", 6))
    assert s.check(("dropsite-min-distance", "live-boar", "==", 255))


def test_sheep_and_forage_too_far_reads_the_bushes():
    s, b = script()
    assert not s.check(("sheep-and-forage-too-far",))
    b.g.map.bushes = {}
    assert s.check(("sheep-and-forage-too-far",))


def test_the_names_give_no_warning():
    s, b = script()
    for f in [("resource-found", "food"), ("dropsite-min-distance", "stone", ">", 1), ("sheep-and-forage-too-far",)]:
        s.check(f)
    assert not s.warned
    assert not s.check(("resource-found", "iron")) and s.warned == {("resource", "iron")}
