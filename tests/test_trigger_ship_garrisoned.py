"""#3780 (epic #3774): the condition "Units Garrisoned" counts the units inside an own transport ship (ref 7). The score
#g7 aoe_gar is the number of units of the ship's cargo, and it is sent only when that number changes."""
import types

from test_gather import FakeServer, grid

from game import gather, scenario, transport

SHIP = {"kind": "unit", "name": "TRANSPORT_SHIP", "player": 1, "uuid": "ship", "ref": 7, "tile": [5.5, 5.5]}


def setup():
    units = [SHIP] + [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": f"v{k}", "tile": [10.5 + k, 10.5]}
                      for k in range(3)]
    server = FakeServer({u["uuid"]: {"Pos": (u["tile"][0], 64.0, u["tile"][1])} for u in units})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], units)).setup()
    g.bots = [types.SimpleNamespace(g=gather.Gather(server, grid([[64] * 16 for _ in range(16)], []), player=2))]
    return server, g


def test_the_score_of_a_transport_ship_is_the_number_of_units_on_board():
    server, g = setup()
    scenario.garrisons(g)
    assert not [c for c in server.log if " aoe_gar " in c]              # empty: no score, no command
    for u in ("v0", "v1", "v2"):
        transport.go_in(g, u, "ship")
    scenario.garrisons(g)
    scenario.garrisons(g)
    assert [c for c in server.log if " aoe_gar " in c] == ["scoreboard players set #g7 aoe_gar 3"]   # once
    transport.out(g, "ship")                                            # all come out on the land
    scenario.garrisons(g)
    assert server.log[-1] == "scoreboard players set #g7 aoe_gar 0"
