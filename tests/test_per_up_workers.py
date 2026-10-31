"""up-assign-builders, up-retask-gatherers, up-drop-resources and up-request-hunters of an AI script (#4875)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build


def scripted(text):
    server, me, b = bot_map()
    b.script = per.Script(per.parse(text), b)
    return b


def builders(b, site):
    return {u for u, v in b.g.villagers.items() if v.site is site}


def test_up_assign_builders_sets_the_builders_of_the_next_site_and_of_a_site_in_construction():
    b = scripted("(defrule (true) => (up-assign-builders c: house c: 3) (disable-self))")
    g = b.g
    old = build.found(g, "HOUSE", build.near(g, "HOUSE", b.center()), free=True)
    b.builder(old)
    assert len(builders(b, old)) == 1
    b.script.step()
    assert len(builders(b, old)) == 3                                  # the rest go at once
    b.builder(old)
    assert len(builders(b, old)) == 3                                  # no more than the number
    new = build.found(g, "HOUSE", build.near(g, "HOUSE", (10, 10)), free=True)
    b.builder(new)
    assert len(builders(b, new)) == 3
    camp = build.found(g, "LUMBER_CAMP", build.near(g, "LUMBER_CAMP", (12, 12)), free=True)
    b.builder(camp)
    assert len(builders(b, camp)) == 1                                 # another type keeps one


def working(b, res, n):
    for u in sorted(b.g.villagers)[:n]:
        v = b.g.villagers[u]
        v.state, v.res, v.site = "chop", res, None


def test_up_retask_gatherers_moves_the_given_number_away():
    b = scripted("(defrule (true) => (up-retask-gatherers wood c: 2) (disable-self))")
    working(b, "wood", 5)
    b.script.step()
    assert sum(v.res == "wood" for v in b.g.villagers.values()) == 3


def test_up_drop_resources_sends_only_the_full_gatherers():
    b = scripted("(defrule (true) => (up-drop-resources wood c: 5) (up-request-hunters c: 2) (disable-self))")
    working(b, "wood", 5)
    loads = dict(zip(sorted(b.g.villagers), (0, 3, 5, 7, 10)))
    for u, k in loads.items():
        b.g.villagers[u].load = k
    b.script.step()
    assert {u for u, v in b.g.villagers.items() if v.state == "to_drop"} == {u for u, k in loads.items() if k >= 5}
    assert not b.script.warned
