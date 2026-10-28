"""game/map_table.py: a right click with the command stick on a pixel of the framed map with no selection moves the
view of the player to the block of that pixel, as a click on the AoE2 minimap (#2788). The player is the camera: a tp
to the ground that keeps the yaw and pitch, the form of the trigger effect "Change View" (#2610)."""
from test_minimap_click import block, click, setup
from test_move_order import moves

from game import map_table


def tps(server):
    return [c for c in server.log if c.startswith("tp ")]


def test_a_click_with_no_selection_moves_the_player_to_the_ground_of_the_pixel():
    server, g = setup()
    server.log.clear()
    x, z = block(40, 64, 0), block(20, 64, 0)
    click(server, x, z)
    map_table.tick(g)
    name = next(n for n in g.people() if n)
    assert tps(server) == [f"tp {name} 40.5 64 20.5"]                  # no rotation: the yaw and pitch stay
    assert not moves(server) and map_table.CLICK not in server.scores


def test_a_click_with_a_selection_does_not_move_the_player():
    server, g = setup()
    g.choose({"m0"}, "m0")
    server.log.clear()
    click(server, 40, 20)
    map_table.tick(g)
    assert moves(server) and not tps(server)


def test_a_click_outside_the_map_does_not_move_the_player():
    server, g = setup()
    server.log.clear()
    click(server, 200, 20)
    map_table.tick(g)
    assert not tps(server) and map_table.CLICK not in server.scores
