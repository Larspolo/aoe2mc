"""#3692: the MONUMENT line that hill.mark adds to aoe2mc.json has no footprint (no target). gather.Map of a later
build.found (Replay.grid) must skip it, else the KeyError stops Gather.run."""
from test_king_of_the_hill import setup

from game import build, gather, hill


def test_a_house_after_the_drawn_monument_keeps_the_game_running():
    server, g = setup(("a", 1, 3.5, 3.5), monument=False)
    hill.tick(g, 1.0)                                                  # draws the monument and marks it
    assert any(o["name"] == "MONUMENT" and "footprint" not in o for o in g.data["objects"])
    gather.Map(g.data)                                                 # no KeyError
    build.found(g, "HOUSE", build.area(g, "HOUSE", (4, 8)))
    assert hill.center(g) == tuple(next(o["tile"] for o in g.data["objects"] if o["name"] == "MONUMENT"))
    x0, x1, z0, z1 = g.monument
    assert not build.free(g, (x0, x1, z0, z1))                         # still blocked for new buildings
