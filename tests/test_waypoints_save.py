"""game/savegame.py: a save keeps the waypoints of the units (#3518): after a load the units walk on to their next points,
as before the save. Fake server, no Minecraft."""
import json

from test_move_order import moves, setup
from test_waypoints import arrive, queue

from game import gather, savegame


def loaded(g):
    server, h = setup(militia=2, villagers=0)
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return server, h


def test_a_loaded_game_has_the_same_waypoints():
    _, g = queue()
    _, h = loaded(g)
    assert h.waypoints == g.waypoints and h.waypoints["m0"]
    assert h.waypoint_at == g.waypoint_at


def test_the_units_walk_on_to_their_next_point_after_a_load():
    server_g, g = queue()
    server, h = loaded(g)
    for game, srv in ((g, server_g), (h, server)):                     # the same leg as the game without the load
        arrive(srv, game)
        srv.log.clear()
        gather.waypoint(game)
    assert moves(server) and moves(server) == moves(server_g)
