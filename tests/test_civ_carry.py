"""game/civs.py CARRY: Aztec villagers carry 3 more resources, Goth hunters 15 more food (AoE2 DE civilization
bonuses, #2270)."""
from test_civ_last import gathered
from test_civ_work import setup

from game import civs


def test_an_aztec_villager_carries_13_wood_and_a_frankish_one_10():
    assert setup("AZTECS").limit("wood") == 13 and setup("FRANKS").limit("wood") == 10
    assert setup("AZTECS").limit("food", "farm") == 13 and setup("AZTECS").limit("gold") == 13


def test_a_goth_hunter_carries_25_food_and_a_goth_farmer_10():
    g = setup("GOTHS")
    assert g.limit("food", "hunt") == 25 and g.limit("food", "farm") == 10 and g.limit("food", "sheep") == 10
    assert g.limit("wood") == 10 and setup("FRANKS").limit("food", "hunt") == 10


def test_the_bonus_adds_to_the_technologies():
    g, base = setup("AZTECS"), setup("FRANKS")
    g.techs.add("WHEELBARROW")
    base.techs.add("WHEELBARROW")
    assert g.limit("wood") == base.limit("wood") + 3 > 13


def test_a_goth_hunter_stops_with_25_food_and_a_shepherd_with_10():
    """The chop step of Gather.step stops at the limit of the gather kind: a deer for a hunter, a sheep for a shepherd."""
    for herd, load in ((False, 25), (True, 10)):
        g = setup("GOTHS")
        v = g.villagers["v"]
        g.map.carcasses[(4, 4)] = 100
        if herd:
            g.map.herds.add((4, 4))
        v.res, v.tree, v.state = "food", (4, 4), "chop"
        for _ in range(5000):
            if v.state != "chop":
                break
            g.step()
        assert v.state != "chop" and v.load == load, herd


def test_the_hunt_lasts_as_long_as_for_other_civilizations():
    """The second part of the Goth bonus ("hunt lasts 20% longer") is a gap of #1088."""
    assert gathered("GOTHS", carcass=(100, False)) == gathered("FRANKS", carcass=(100, False)) == 100
    assert civs.carry(setup("FRANKS"), "hunt") == 0
