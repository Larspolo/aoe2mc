"""game/build.py: the ghost of a dock stands on the cell that the plugin ghost shows (#2058). The plugin ray
(Ghost.java tick) stops on the first water surface, so the dock takes the cell of fleet.pick too. Fake server."""
from test_dock_build import shore_map

from game import build, fleet, gather


def look(server, pos, rot):
    server.entities["Steve"].update({"Pos": pos, "Rotation": rot})
    server.scores[build.OBJECTIVE] = server.chosen                     # the dock is chosen
    return (pos[0], pos[1] + 1.62, pos[2]), gather.direction(*rot)


def test_the_dock_ghost_at_the_shore_is_green():
    server, g = shore_map()
    eye, d = look(server, (12.5, 64.0, 12.5), (-90.0, 40.0))
    assert fleet.pick(g, eye, d) == (15, 12)
    build.ghosts(g)
    assert g.ghosts["Steve"][:2] == ["DOCK", "green"]


def test_the_dock_ghost_on_the_open_water_turns_red():
    server, g = shore_map()
    look(server, (12.5, 64.0, 12.5), (-90.0, 40.0))
    build.ghosts(g)                                                    # green at the shore first
    eye, d = look(server, (14.5, 70.0, 12.5), (-90.0, 50.0))
    assert fleet.pick(g, eye, d) == (21, 12)                          # the first water surface, as the plugin ray
    build.ghosts(g)
    assert g.ghosts["Steve"][:2] == ["DOCK", "red"]
    assert build.place(g, "Steve", "DOCK", eye, d) is None and not g.sites
