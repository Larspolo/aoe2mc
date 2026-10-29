"""game/civs.py CARRY: Aztec villagers carry more resources, Goth hunters more food (AoE2 DE civilization bonuses,
#2270)."""
from test_civ_last import gathered
from test_civ_work import setup

from game import civs


def test_an_aztec_villager_carries_more_than_a_frankish_one():
    aztec, frank = setup("AZTECS"), setup("FRANKS")
    for kind in (("wood",), ("food", "farm"), ("gold",)):
        assert aztec.limit(*kind) > frank.limit(*kind), kind


def test_a_goth_hunter_carries_more_food_and_a_goth_farmer_not():
    g, frank = setup("GOTHS"), setup("FRANKS")
    assert g.limit("food", "hunt") > frank.limit("food", "hunt")
    for kind in (("food", "farm"), ("food", "sheep"), ("wood",)):
        assert g.limit(*kind) == frank.limit(*kind), kind


def test_the_bonus_adds_to_the_technologies():
    g, base = setup("AZTECS"), setup("FRANKS")
    bonus = g.limit("wood") - base.limit("wood")
    g.techs.add("WHEELBARROW")
    base.techs.add("WHEELBARROW")
    assert g.limit("wood") == base.limit("wood") + bonus and base.limit("wood") > setup("FRANKS").limit("wood")


def test_a_goth_hunter_and_a_shepherd_stop_at_their_limits():
    """The chop step of Gather.step stops at the limit of the gather kind: a deer for a hunter, a sheep for a shepherd."""
    for herd, kind in ((False, "hunt"), (True, "sheep")):
        g = setup("GOTHS")
        load = g.limit("food", kind)
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


def test_other_civilizations_hunt_as_in_aoe2():
    """The second part of the Goth bonus ("hunt lasts 20% longer"): tests/test_goth_hunt.py (#2375)."""
    assert gathered("FRANKS", carcass=(100, False)) == 100
    assert civs.carry(setup("FRANKS"), "hunt") == 0
