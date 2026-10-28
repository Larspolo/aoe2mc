"""game/train.py: a dead own soldier or ship leaves g.soldiers and the selection at the census, as a dead villager
(#3122). Fake servers."""
from test_castle_upgrades import setup
from test_ship_gather import fish_map, play

from game import fleet, train


def test_a_sunk_fishing_ship_stops_fishing_after_the_census():
    server, g, uuid = fish_map()
    v = g.ships[uuid]
    fleet.fish(g, {uuid}, (20, 12))
    play(g, 20)
    assert v.state == "chop"
    del server.entities[uuid]                                          # its boat sinks
    train.census(g)
    food = g.stock["food"]
    play(g, 100)
    assert uuid not in g.soldiers and uuid not in g.ships and g.stock["food"] == food


def test_a_dead_soldier_leaves_the_lists_and_gets_no_more_commands():
    server, g = setup()
    u = next(iter(g.soldiers))
    g.selected = {u}
    del server.entities[u]
    train.census(g)
    assert u not in g.soldiers and u not in g.selected
    server.log.clear()
    train.census(g)
    assert not [c for c in server.log if f" {u} " in c]
