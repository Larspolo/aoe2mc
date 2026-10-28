"""The edge of the line of sight in the world (#3330, Sight.java): the plugin draws dust particles on the ground along
each side between a tile in sight and a tile out of sight of the fog of the team (Minimap.fogOf), only for the players
of that team. `aoe sightedge count` gives the sides that a draw near a place uses."""
import shutil

import pytest


@pytest.mark.mc
def test_the_edge_has_the_sides_between_seen_and_unseen_tiles(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        def sides(*a):
            return int(game.command("aoe sightedge count " + " ".join(map(str, a))).split()[2])
        game.command("team add p1")
        assert sides("p1", 14, 14, 100) == 0                           # no fog: no edge
        assert "Minimap fog: 16 tiles" in game.command("aoe minimap fog 4 16 p1")
        assert "Minimap see: 9 tiles" in game.command("aoe minimap see p1 2,2,4 3,2,4 4,2,4")
        assert sides("p1", 14, 14, 100) == 12                          # tiles 2 to 4: 3 sides on each of 4 edges
        assert sides("p1", 14, 14, 2) == 0                             # only the middle tile: all its neighbors seen
        assert sides("p1", 200, 200, 20) == 0                          # far from the sight
        assert "Minimap dim: 3 tiles" in game.command("aoe minimap dim p1 3,2,4")   # the middle row out of sight
        assert sides("p1", 14, 14, 100) == 16                          # two strips of 3 × 1 tiles: 8 sides each
        assert "Minimap see: 1 tiles" in game.command("aoe minimap see p1 0,0,0")
        assert sides("p1", 0, 0, 8) == 2                               # the map border is no edge
        assert sides("-", 14, 14, 100) == 0                            # the fog without a team (the replay) is off
        assert "Sight edge off: 0 players" in game.command("aoe sightedge @a off")
        assert game.command("aoe minimap fog off p1").strip() == "Minimap fog: off"
        assert sides("p1", 14, 14, 100) == 0                           # "polo" or Spies: no fog, no edge
