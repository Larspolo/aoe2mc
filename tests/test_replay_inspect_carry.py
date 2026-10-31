"""Live replay: the info line of a gathering villager shows the load that it carries (inspect(), #5368). Fake RCON."""
import json

import gather
from test_replay_inspect import facing, setup


def line(r):
    (c,) = [c for c in r.inspect(10000, clock=lambda: 0.0) if " actionbar " in c]
    return "".join(p["text"] for p in json.loads(c.split(" actionbar ", 1)[1]))


def gatherer(r, res, load, tech=None):
    """Villager 7 (player 2) gathers res with load gather steps; tech (a gather.CARRY name) is researched at time 0."""
    r.working.update({7: 1})
    r.units[7].res, r.units[7].load = res, load
    if tech:
        r.learned = {2: [(0, tech)]}


def test_a_load_above_the_capacity_shows_the_rest_and_its_resource(monkeypatch):
    tech = "TEST_CARRY"                                             # the default rules have no carry technology
    monkeypatch.setitem(gather.CARRY, tech, 4)
    cap = gather.BASE_CARRY + gather.CARRY[tech]
    r = setup()
    facing(r, 40.0)
    gatherer(r, "wood", cap + 3, tech)
    assert " | carries 3 wood | " in line(r)


def test_a_load_below_the_capacity_is_the_load():
    r = setup()
    facing(r, 40.0)
    gatherer(r, "gold", gather.BASE_CARRY - 1)
    assert " | carries " + str(gather.BASE_CARRY - 1) + " gold | " in line(r)


def test_a_full_trip_shows_no_carry_field():
    r = setup()
    facing(r, 40.0)
    gatherer(r, "wood", 2 * gather.BASE_CARRY)
    assert "carries" not in line(r)


def test_a_villager_that_does_not_gather_shows_no_carry_field():
    r = setup()
    facing(r, 40.0)
    r.units[7].res, r.units[7].load = "wood", gather.BASE_CARRY - 1
    assert "carries" not in line(r)
