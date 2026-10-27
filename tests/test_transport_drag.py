"""game/transport.py and game/gather.py: the units inside a transport ship (g.cargo) and the drags of the selection box
(g.holds) are two tables (#1511). Before, both were g.holds: a loaded ship stopped Gather.release() with a TypeError,
and a drag stopped transport.tick() and was lost."""
from test_transport_ship import setup

from game import transport


def test_a_loaded_transport_ship_and_a_drag_at_the_same_time():
    server, g = setup()
    g.cargo = {"ship": ["m", "s"]}
    g.holds["Steve"] = t = g.clock()                                    # a held right click with the wand
    g.release()                                                         # no TypeError: 0 s without a use, still held
    transport.tick(g)                                                   # no TypeError: the drag is no sunk ship
    assert g.holds == {"Steve": t} and g.cargo == {"ship": ["m", "s"]}
    assert not any(c.startswith("kill") for c in server.log)


def test_the_tables_stay_apart_when_the_ship_loads():
    server, g = setup()
    g.holds["Steve"] = g.clock()
    transport.go_in(g, "m", "ship")
    assert g.cargo == {"ship": ["m"]} and set(g.holds) == {"Steve"}
