"""game/gather.py work_time: Georgian villagers in the 21-tile square around a complete own Fortified Church gather
faster (AoE2 DE wiki "Georgians", #2377). Fake server, no Minecraft."""
import pytest
from test_civ_work import setup

NEAR, FAR = (11, 14, 6, 9), (21, 24, 6, 9)                            # centers 5 and 15 tiles east of the villager (7.5, 7.5)


def chop_time(civ, *churches, done=True):
    g = setup(civ)
    for rect in churches:
        g.sites.append({"name": "FORTIFIED_CHURCH", "player": 1, "done": done, "footprint": list(rect)})
    v = g.villagers["v"]
    return g.work_time("wood", pos=(v.pos[0], v.pos[2])), g.work_time("wood")


def test_a_georgian_lumberjack_near_an_own_church_chops_faster():
    near, plain = chop_time("GEORGIANS", NEAR)
    assert near < plain
    assert chop_time("GEORGIANS", NEAR, FAR)[0] == chop_time("GEORGIANS", NEAR, (10, 13, 9, 12))[0] == near   # no stack


def test_a_far_church_a_construction_site_and_an_armenian_church_give_no_bonus():
    base = chop_time("GEORGIANS")[0]
    assert chop_time("GEORGIANS", FAR)[0] == base
    assert chop_time("GEORGIANS", NEAR, done=False)[0] == base
    assert chop_time("ARMENIANS", NEAR)[0] == chop_time("ARMENIANS")[0] == setup("ARMENIANS").work_time("wood")


def test_the_chop_step_gathers_faster_near_the_church():
    """Gather.step: the same time gives the Georgian villager near the church about the rate of work_time more wood."""
    def chopped(*churches):
        g = setup("GEORGIANS")
        for rect in churches:
            g.sites.append({"name": "FORTIFIED_CHURCH", "player": 1, "done": True, "footprint": list(rect)})
        v = g.villagers["v"]
        g.map.trees[(8, 7)] = 1000
        v.res, v.tree, v.state, g.carry = "wood", (8, 7), "chop", 1000
        for _ in range(400):
            g.step()
        return v.load
    plain, near = chopped(), chopped(NEAR)
    rate = chop_time("GEORGIANS", NEAR)[1] / chop_time("GEORGIANS", NEAR)[0]
    assert plain > 20 and near == pytest.approx(plain * rate, abs=1)
