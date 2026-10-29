"""game/autoscout.py: a scout on Auto Scout walks to the nearest tile that its side did not explore, then to the next
one when it stands there; a new order ends it, and a side that explored all tiles ends it too (#3702)."""
from game import autoscout, gather, savegame

from test_gather import FakeServer, grid


def setup(monkeypatch):
    """A scout of player 1 at tile (1, 1) on a 16 × 16 map (tile size 1) with the corner x, y < 4 explored."""
    objects = [{"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": "s-1", "tile": [1.5, 1.5]}]
    server = FakeServer({"s-1": {"Pos": (1.5, 64.0, 1.5)}, "Steve": {}})
    g = gather.Gather(server, grid([[64] * 16 for _ in range(16)], objects)).setup()
    g.explored = {(x, y) for x in range(4) for y in range(4)}
    where = {"s-1": (1.5, 64.0, 1.5)}
    monkeypatch.setattr(g, "positions", lambda uuids: {u: where[u] for u in uuids if u in where})
    server.log.clear()
    return server, g, where


def test_a_scout_walks_to_the_nearest_unexplored_tile_and_then_to_the_next(monkeypatch):
    server, g, where = setup(monkeypatch)
    autoscout.start(g, {"s-1"})
    assert server.log == ["aoe moveto s-1 1 64 4"]                     # (1, 4) and (4, 1) are as near: the lower x
    server.log.clear()
    where["s-1"] = (1.5, 64.0, 2.5)                                    # it walks: no new order
    autoscout.tick(g)
    assert server.log == []
    where["s-1"] = (1.5, 64.0, 4.5)                                    # it stands on its goal
    g.explored.add((1, 4))
    autoscout.tick(g)
    assert server.log == ["aoe moveto s-1 0 64 4"]


def test_a_move_order_ends_the_scouting(monkeypatch):
    server, g, _ = setup(monkeypatch)
    autoscout.start(g, {"s-1"})
    g.new_order({"s-1"})
    assert g.scouting == {}


def test_a_side_that_explored_all_tiles_stops_the_scout(monkeypatch):
    server, g, _ = setup(monkeypatch)
    g.explored = {(x, y) for x in range(16) for y in range(16)}
    autoscout.start(g, {"s-1"})
    assert g.scouting == {} and server.log == []


def test_a_save_and_a_load_keep_the_scouting(monkeypatch):
    server, g, _ = setup(monkeypatch)
    autoscout.start(g, {"s-1"})
    assert "scouting" in savegame.ORDERS
    assert savegame.unpack(savegame.pack(g.scouting)) == g.scouting
