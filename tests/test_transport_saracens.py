"""A Saracen transport ship carries more units, as in AoE2 DE (#2344): the key "transport". The map of
test_transport_board_side; the units go in with transport.go_in."""
from test_transport_board_side import setup

from game import civs, transport


def board(civ, n):
    """n militia of player 1 (civilization civ) go into the own transport ship; returns the units inside."""
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    for i in range(n):
        g.soldiers[f"u{i}"] = "MILITIA"
        transport.go_in(g, f"u{i}", "ship")
    return g.cargo["ship"]


def test_a_saracen_transport_ship_takes_more_units():
    more = civs.value("transport", "SARACENS", 0)
    assert more > 0 and len(board("SARACENS", transport.SIZE + more + 1)) == transport.SIZE + more
    inside = board("BRITONS", transport.SIZE + 1)
    assert len(inside) == transport.SIZE and f"u{transport.SIZE}" not in inside   # the next unit stays on the land
