"""A jump of the replay input with the float game time of Replay.run (#803): the program must not stop."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_jump import timeline  # noqa: E402

import replay  # noqa: E402
import replay_input as ri  # noqa: E402


@pytest.mark.parametrize("n, to", [(ri.JUMP, "Jump to 02:01"), (ri.JUMP5, "Jump to 06:01"),
                                   (ri.JUMP10, "Jump to 11:01")])
def test_a_jump_text_with_a_float_time(n, to):
    control = {"time": 61234.5}
    assert ri.apply(n, control) == to and control["jump"] == 61234.5 + ri.JUMPS[n]


def test_a_jump_of_the_input_in_a_running_replay():
    game, said = Clock(), []

    def poll(control):                                                  # the action of the ender pearl at 0:60
        if game.now >= 60 and not said:
            said.append(ri.apply(ri.JUMP5, control))
    replay.Replay(game, data(timeline())).run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll)
    assert isinstance(said[0], str) and re.fullmatch(r"Jump to 06:0\d", said[0])
    assert set(game.at) == {"t30000", "t400000"}                        # 3:20 is skipped, 6:40 comes after it


@pytest.mark.mc
def test_a_trigger_jump_on_a_server(tiny_world, tmp_path):
    import json
    import shutil
    import threading
    import time
    import urllib.parse

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
        inp = ri.Input(game)
        inp.setup()
        at, command = {}, game.command

        def timed(c):
            for one in [urllib.parse.unquote_plus(x) for x in c.split(" ")[2:]] if c.startswith("aoe batch ") else [c]:
                if one.startswith("tellraw @a "):                      # also in a batch (#2761)
                    at[json.loads(one[len("tellraw @a "):])[-1]["text"]] = time.monotonic() - t0
            return command(c)
        game.command = timed

        def player():                                                  # /trigger aoe_replay set 3 at 2 s
            time.sleep(2 - (time.monotonic() - t0))
            command(f"scoreboard players set aoe2mc {ri.OBJECTIVE} {ri.JUMP}")
        events = [{"time": t, "player": 1, "kind": "chat", "text": f"t{t}"} for t in (1000, 30000, 70000)]
        t0 = time.monotonic()
        th = threading.Thread(target=player)
        th.start()
        replay.Replay(game, data(events)).run(1.0, log=None, poll=inp)
        th.join()
        assert set(at) == {"t1000", "t70000"} and 9 < at["t70000"] < 12, at   # 0:02 + 60 s, then 8 s
