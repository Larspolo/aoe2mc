"""The guide of an owner replay check (game/watch.py) keeps the owner in adventure mode (#1642): the plugin changes the
mode on a double tap of Shift only between adventure and spectator (Viewer.onInput), so creative mode stopped --follow."""
import os
import shutil
import sys
import time
from types import SimpleNamespace

import pytest
from test_watch import Game, chop_replay

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import replay  # noqa: E402
import watch  # noqa: E402


def test_place_puts_the_players_in_adventure_mode_with_the_viewer_tag():
    game = Game()
    game.online = ["Lars"]
    g = watch.Guide(game, [], 1.0, [], log=lambda s: None)
    g.r = chop_replay()
    g.place({"where": "unit:villager"})
    assert "gamemode adventure @a" in game.sent
    assert not any(c.startswith("gamemode creative") for c in game.sent)
    assert game.sent.index(f"tag @a add {replay.VIEWER}") < game.sent.index("gamemode adventure @a")   # Viewer.onMode: flight


@pytest.mark.mc
def test_a_double_tap_of_shift_after_place_gives_the_spectator_view(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(10)                                                 # the world is drawn: slow frames lose keys
        game.command("gamemode creative aoe2mc")                      # the mode before #1642
        g = watch.Guide(game, [], 1.0, [], log=lambda s: None)
        g.r = SimpleNamespace(T=4, starts=[])
        g.place({"where": "tile:2,3"})
        time.sleep(2)                                                  # Viewer.onMode gives the flight after 20 ticks

        def mode():
            return game.command("data get entity aoe2mc playerGameType").rsplit(" ", 1)[-1]

        assert mode() == "2"                                           # adventure
        for _ in range(2):
            client.xdo("keydown", "Shift_L")                           # 0.15 s: the client reads the key once a
            time.sleep(0.15)                                           # frame (test_replay_spectate.py)
            client.xdo("keyup", "Shift_L")
            time.sleep(0.15)
        time.sleep(1.5)
        assert mode() == "3"                                           # spectator: --follow can start
