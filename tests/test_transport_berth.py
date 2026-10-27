"""Land units board an own transport ship only at the shore: the ship sails to the water next to the shore cell of
the units first, as in AoE2 (the owner, #2055: "they can still load while the boat is not near the coast")."""
import pytest
from test_transport_ship import setup

from game import fleet, transport


def sail(server, g, ship="ship"):
    """Sail the ship to the end of its path; the fake server follows its /tp steps."""
    v = g.ships[ship]
    while v.path:
        fleet.tick(g, 1.0)
        server.entities[ship]["Pos"] = v.pos


@pytest.mark.parametrize("x", [17.5, 20.5, 23.5])                       # 4, 7 and 10 tiles from the land (x < 14)
def test_the_ship_sails_to_the_shore_and_the_units_go_in_there(x):
    server, g = setup()                                                # tile size 1: SHORE is 3 blocks
    server.entities["ship"]["Pos"] = (x, 63.0, 5.5)
    assert transport.order(g, "Steve", "ship")
    assert g.loading == {u: ("ship", (13, 5)) for u in ("m", "s", "v")} and g.berths == {"ship": (14, 5)}
    assert g.ships["ship"].path[-1] == (14, 5)
    for u in ("m", "s", "v"):
        server.entities[u]["Pos"] = (13.5, 64.0, 5.5)
    transport.tick(g)
    assert not vars(g).get("cargo") and set(g.loading) == {"m", "s", "v"}   # the ship is not at the shore yet
    sail(server, g)
    transport.tick(g)
    assert g.cargo == {"ship": ["m", "s", "v"]} and not g.loading and not g.berths
    assert server.entities["ship"]["Pos"] == (14.5, 63.0, 5.5)


def test_a_unit_on_the_way_waits_for_the_ship_at_the_shore():
    server, g = setup()
    server.entities["ship"]["Pos"] = (20.5, 63.0, 5.5)
    assert transport.order(g, "Steve", "ship")
    sail(server, g)
    server.entities["m"]["Pos"] = (9.5, 64.0, 5.5)                     # 4 blocks from the shore cell
    transport.tick(g)
    assert "m" in g.loading and "m" not in vars(g).get("cargo", {}).get("ship", [])
    server.entities["m"]["Pos"] = (13.5, 64.0, 5.5)
    transport.tick(g)
    assert "m" in g.cargo["ship"]


def test_a_boarding_order_ends_an_unload_order():
    server, g = setup()
    g.unloads = {"ship": (3, 3)}
    assert transport.order(g, "Steve", "ship") and not g.unloads


def test_no_water_path_to_the_shore_no_boarding():
    server, g = setup()
    server.entities["ship"]["Pos"] = (20.5, 63.0, 5.5)
    real = g.map.wet
    g.map.wet = lambda x, z: real(x, z) and x != 17                   # a dam cuts the ship from the shore
    assert not transport.order(g, "Steve", "ship") and not vars(g).get("loading")
