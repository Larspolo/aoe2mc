"""A loaded transport ship sent to a land cell far from the water sails to the nearest shore, unloads there, and the
units walk on to the clicked cell, as in AoE2 DE (#1515). Before, fleet.goals took only the water within NEAR tiles of
the clicked cell, and the ship did not move."""
import math

from test_transport_ship import setup

from game import fleet, transport


def test_a_far_land_click_gives_the_nearest_water():
    server, g = setup()                                                # land at x < 14, water at x >= 14
    assert fleet.goals(g, (2, 5), 1) == [(14, 5)]                      # 12 cells from the water (NEAR: 3)
    assert fleet.goals(g, (12, 5), 1) == [(14, 5)]


def test_a_loaded_ship_sent_far_inland_unloads_at_the_shore_and_the_units_walk_on():
    server, g = setup()
    g.cargo = {"ship": ["m", "v"]}
    g.choose({"ship"}, "ship")
    out = g.walk_to("Steve", (2, 15))                                  # 10 tiles from the water
    assert g.map.wet(*out["ship"]) and g.unloads == {"ship": (2, 15)}
    for _ in range(30):
        fleet.tick(g, 1.0)
    transport.tick(g)
    assert not g.cargo and not g.unloads
    tps = [c.split() for c in server.log if c.startswith("tp ")]
    shore = {(math.floor(float(t[2])), math.floor(float(t[4]))) for t in tps if t[1] in ("m", "v")}
    assert shore and all(x >= 10 for x, _ in shore), shore             # out at the shore, not at the far cell
    assert any(c.startswith("aoe moveto m 2.5 ") or c.startswith("aoe moveto m 3.5 ") for c in server.log)
    assert g.villagers["v"].state == "to_rally" and math.dist(g.villagers["v"].goal, (2, 15)) <= 2
    assert g.selected == {"ship"}                                      # the selection stays


def test_a_ship_without_units_sails_to_the_nearest_water_of_a_far_click():
    server, g = setup()
    g.choose({"ship"}, "ship")
    out = g.walk_to("Steve", (2, 15))
    assert out["ship"] == (14, 15) and not getattr(g, "unloads", {})
