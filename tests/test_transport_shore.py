"""A loaded transport ship sent to a land cell unloads its units on the shore next to the ship, and they walk to the
clicked cell, as in AoE2 DE (#1652). Before, a click within SHORE tiles of the ship put the units at the clicked cell
with /tp (the owner's check of #1492: "the units teleported to the exact spot")."""
import math

import pytest
from test_transport_ship import setup

from game import fleet, transport


@pytest.mark.parametrize("inland", [2, 4, 10])
def test_the_units_come_out_next_to_the_ship_and_walk_to_the_click(inland):
    server, g = setup()                                                # tile size 1: land at x < 14, water at x >= 14
    g.cargo = {"ship": ["m", "v"]}
    g.choose({"ship"}, "ship")
    click = (14 - inland, 15)
    g.walk_to("Steve", click)
    for _ in range(30):
        fleet.tick(g, 1.0)
    server.entities["ship"]["Pos"] = g.ships["ship"].pos                # the fake server does not run `execute ... tp`
    assert g.map.wet(*g.ships["ship"].cell) and g.ships["ship"].cell[1] == 15
    server.log.clear()
    transport.tick(g)
    assert not g.cargo and not g.unloads
    ship = g.pos("ship")
    tps = {t[1]: (float(t[2]), float(t[4])) for t in (c.split() for c in server.log if c.startswith("tp "))}
    assert set(tps) == {"m", "v"}
    for x, z in tps.values():
        assert math.floor(x) == 13 and math.dist((x, z), (ship[0], ship[2])) <= 2.5, tps   # the shore at the ship
    assert any(c.startswith("aoe moveto m ") for c in server.log)                         # then a move order
    goal = next(c.split()[3:6:2] for c in server.log if c.startswith("aoe moveto m "))
    assert math.dist(tuple(map(float, goal)), (click[0] + 0.5, click[1] + 0.5)) <= 2
    assert g.villagers["v"].state == "to_rally" and math.dist(g.villagers["v"].goal, click) <= 2
