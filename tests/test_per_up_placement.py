"""The placement commands of AI scripts: up-build-line, up-can-build-line, up-set-placement-data and up-build
place-control, up-reset-placement (#4972). The map of test_bot_gather: the bot is player 2, its town center at tile 21, 21."""
import math

from test_bot_gather import bot_map

from game import per


def script(text, goals=None):
    server, me, b = bot_map()
    b.g.stock.update(food=1000, wood=1000, gold=1000, stone=1000)
    s = per.Script(per.parse(text), b)
    s.goals.update(goals or {})
    s.step()
    return s, b


def sites(b, name):
    return [s for s in b.g.sites if s["name"] == name]


def middle(site):
    x0, x1, z0, z1 = site["footprint"]
    return (x0 + x1) / 2, (z0 + z1) / 2


def test_up_build_line_puts_a_line_of_houses_between_two_points():
    s, b = script("(defrule (true) => (up-build-line 41 43 c: house) (disable-self))", {41: 8, 42: 12, 43: 12, 44: 12})
    houses = sites(b, "HOUSE")
    assert len(houses) == 3 and {h["footprint"][2] for h in houses} == {houses[0]["footprint"][2]}   # one row
    assert sorted(h["footprint"][0] for h in houses) == [7, 9, 11]                                   # one house apart
    assert not s.warned


def test_up_can_build_line_is_false_on_a_building():
    s, b = script("""(defrule (up-can-build-line 0 41 c: house) => (set-goal 1 1))
(defrule (up-can-build-line 0 43 c: house) => (set-goal 2 1))""", {41: 8, 42: 12, 43: 21, 44: 21})
    assert s.goals.get(1) == 1 and 2 not in s.goals                     # tile 21, 21: the town center


def test_up_set_placement_data_moves_the_site_behind_the_town_center():
    text = "(defrule (true) => {} (up-build {} 0 c: house) (disable-self))"
    _, normal = script(text.format("", "place-normal"))
    s, behind = script(text.format("(up-set-placement-data my-player-number -1 c: -6)", "place-control"))
    centre = (16, 16)
    assert math.dist(middle(sites(behind, "HOUSE")[0]), centre) > math.dist(middle(sites(normal, "HOUSE")[0]), centre) + 3
    assert not s.warned


def test_up_reset_placement_clears_the_pending_placement():
    s, b = script("(defrule (true) => (disable-self))")
    s.unplaced.add("HOUSE")
    assert s.check(("up-pending-placement", "c:", "house"))
    s.act(0, ("up-reset-placement", "c:", "house"))
    assert not s.check(("up-pending-placement", "c:", "house"))
