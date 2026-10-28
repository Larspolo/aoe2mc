"""The flares of the game program on the minimap of the map item (#2676, epic #2580): on Paper flare.put() also sends
`aoe minimap flare X Z pN TICKS VIEWERS`, and the plugin draws the cross only for the players on the viewer teams (the
own team and its allies). The replay flare without VIEWERS shows to all players (#2405). Fake server and Paper."""
import shutil
import time

import pytest
from test_flare_allies import setup

from game import flare


def marks(server):
    return [c for c in server.log if c.startswith("aoe minimap flare")]


def test_on_paper_a_flare_is_a_cross_for_the_own_and_allied_teams():
    server, g = setup({"0": {}, "1": {"team": 1}, "2": {"team": 2}, "3": {"team": 1}})
    g.paper = True
    flare.put(g, "Steve", 5, 65, 9)
    assert marks(server) == [f"aoe minimap flare 5 9 p1 {flare.SECONDS * 20} p1,p3"]


def test_without_allies_only_the_own_team_and_on_vanilla_no_cross():
    server, g = setup({"0": {}, "1": {}, "2": {}})
    g.paper = True
    flare.put(g, "Steve", 5, 65, 9)
    assert marks(server) == [f"aoe minimap flare 5 9 p1 {flare.SECONDS * 20} p1"]
    server, g = setup({"0": {}, "1": {"team": 1}, "3": {"team": 1}})
    g.paper = False
    flare.put(g, "Steve", 5, 65, 9)
    assert marks(server) == []


@pytest.mark.mc
def test_the_plugin_draws_the_cross_only_for_the_viewer_teams(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        game.command("item replace entity aoe2mc weapon.mainhand with minecraft:filled_map[minecraft:map_id=0]")
        for c in ("team add p7", "team modify p7 color red", "team add p8", "team modify p8 color blue",
                  "team join p8 aoe2mc"):
            game.command(c)
        assert "Minimap: on" in game.command("aoe minimap on")
        red = str(28 * 4 + 2)

        def colors(x, z, seconds=3):                                   # the cross blinks: look for 3 s
            out = set()
            for _ in range(seconds * 4):
                out.add(game.command(f"aoe minimap tile {x} {z} p8").split()[3])
                time.sleep(0.25)
            return out
        assert "outside" not in game.command("aoe minimap flare 20 20 p7 400 p7")   # p8 is no viewer
        assert red not in colors(20, 20)
        assert "outside" not in game.command("aoe minimap flare 40 40 p7 400 p7,p8")   # an ally of p7
        assert red in colors(40, 40)
        assert "outside" not in game.command("aoe minimap flare 60 20 p7 400")       # the replay: all players
        assert red in colors(60, 20)
