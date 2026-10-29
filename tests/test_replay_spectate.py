"""Live replay: a viewer changes between spectator mode and adventure mode with flight (#910, owner decision #782)."""
import os
import shutil
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay_input import Scores, poll  # noqa: E402

import replay  # noqa: E402
import replay_input as ri  # noqa: E402


def test_the_spectator_item_is_on_paper_only():
    slot, _, name = ri.ITEMS[ri.SPECTATE]
    assert f'item_name="{name}"' in ri.item(ri.SPECTATE)
    paper, vanilla = Scores(), Scores("vanilla")
    poll(paper, {})
    poll(vanilla, {})
    assert any(f"hotbar.{slot}" in c and f"aoe_replay:{ri.SPECTATE}" in c for c in paper.sent)
    assert not any(f"hotbar.{slot}" in c for c in vanilla.sent)           # no plugin: no way back from spectator


def test_a_click_on_the_item_makes_only_that_player_a_spectator():
    game, control = Scores(), {"speed": 1.0, "paused": False}
    game.click("anna", ri.SPECTATE)
    poll(game, control)
    assert f"gamemode spectator @a[scores={{aoe_replay={ri.SPECTATE}}}]" in game.sent
    assert control == {"speed": 1.0, "paused": False}                     # no other action
    assert game.scores["anna"]["aoe_replay"] == 0


def test_the_viewer_tag_of_the_replay_is_the_tag_of_the_plugin():
    java = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game", "plugin", "src",
                             "main", "java", "aoe2mc", "Viewer.java")).read()
    assert f'TAG = "{replay.VIEWER}"' in java


@pytest.mark.mc
def test_a_double_tap_of_shift_changes_the_game_mode_on_a_server(tiny_world, tmp_path):
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

        def mode():
            return game.command("data get entity aoe2mc playerGameType").rsplit(" ", 1)[-1]

        def mayfly():
            return game.command("data get entity aoe2mc abilities.mayfly").rsplit(" ", 1)[-1]

        def taps(n):
            for _ in range(n):
                client.xdo("keydown", "Shift_L")                       # 0.15 s: the client reads the key once a
                time.sleep(0.15)                                       # frame, and software frames are slow (#1213)
                client.xdo("keyup", "Shift_L")
                time.sleep(0.15)
            time.sleep(1.5)

        game.command(f"tag aoe2mc add {replay.VIEWER}")
        game.command("gamemode spectator aoe2mc")
        time.sleep(1)
        taps(1)
        assert mode() == "3"                                           # one tap: it stays a spectator
        taps(2)
        assert (mode(), mayfly()) == ("2", "1b")                       # adventure mode with flight
        inp, control = ri.Input(game), {"speed": 1.0, "paused": False}
        inp.setup()
        inp(control)                                                   # the hotbar items
        client.key("8")                                                # hotbar slot 7: "Spectator view"
        time.sleep(0.5)
        client.xdo("click", "3")
        time.sleep(1)
        inp.last = -float("inf")
        inp(control)
        assert mode() == "3"
        taps(2)
        assert mode() == "2"
        taps(2)
        assert mode() == "3"                                           # from adventure mode back to spectator
        game.command("gamemode adventure aoe2mc")                     # the start view of the replay (#737)
        time.sleep(2)                                                  # Viewer.LATER ticks
        assert mayfly() == "1b"
