"""game/monk.py: a relic that drops on a water cell lies on the nearest free land cell, so a monk can take it (#3119).
Fake server."""
from test_gather import grid
from test_monk_heal import HealServer

from game import gather, monk


def setup():
    """A 24 × 24 map (tile size 1) with water at x >= 12: an own monk at (5.5, 5.5), a second own monk, a relic
    at block (5, 5), an own monastery."""
    rows = [[64] * 24 for _ in range(24)]
    for z in range(24):
        for x in range(12, 24):
            rows[z][x] = "-"
    objects = [{"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk", "tile": [5.5, 5.5]},
               {"kind": "unit", "name": "MONK", "player": 1, "uuid": "monk2", "tile": [6.5, 5.5]},
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [5.5, 5.5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "footprint": [14, 2, 18, 6]}]
    server = HealServer({"monk2": {"Pos": (6.5, 64.0, 5.5), "Health": 30.0, "Max": 30.0}})
    g = gather.Gather(server, grid(rows, objects)).setup()
    g.paper = True
    g.choose({"monk"}, "monk")
    return server, g


def test_a_relic_that_drops_on_water_lies_on_the_nearest_land():
    server, g = setup()
    g.relics[0].update(at=None, monk="monk")                           # the monk carries it, then dies on the water
    g.carrier_at["monk"] = (15.5, 64.0, 5.5)
    monk.relic_tick(g, monk.EVERY)
    assert g.relics[0]["at"] == (11, 5)                                # the nearest free land cell
    assert "setblock 11 64 5 minecraft:decorated_pot keep" in server.log
    g.choose({"monk2"}, "monk")
    assert monk.order(g, "Steve", (11, 5))                             # the second monk can take it


def test_a_relic_that_drops_on_free_land_stays_on_its_cell():
    server, g = setup()
    g.relics[0].update(at=None, monk="monk")
    g.carrier_at["monk"] = (9.5, 64.0, 5.5)
    monk.relic_tick(g, monk.EVERY)
    assert g.relics[0]["at"] == (9, 5)
    assert "setblock 9 64 5 minecraft:decorated_pot keep" in server.log
