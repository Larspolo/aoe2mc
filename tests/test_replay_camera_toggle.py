"""Live replay: the automatic camera on and off in the replay menu (#3369). Fake RCON."""
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import Fake, data  # noqa: E402
from test_replay_input import Scores, poll  # noqa: E402

import replay  # noqa: E402
import replay_input as ri  # noqa: E402

SHOTS = [{"time": 2000, "tile": [5, 6], "why": "build"}, {"time": 30000, "tile": [10.5, 3], "why": "fight"},
         {"time": 50000, "tile": [1, 1], "why": "build"}]


def test_the_trigger_switches_the_camera_and_the_menu_has_the_item():
    game, control = Scores(), {"speed": 1.0, "paused": False, "time": 0, "camera": None}
    game.scores["ben"]["aoe_replay"] = ri.CAMERA                # /trigger aoe_replay set CAMERA
    poll(game, control)
    assert control["camera"] == "auto"
    game.scores["ben"]["aoe_replay"] = ri.CAMERA                # the next click switches it off again
    poll(game, control)
    assert control["camera"] is None
    game.sent.clear()
    ri.Input(game).open_menu("ben")
    assert any(urllib.parse.quote("Camera: free") in c for c in game.sent)


def test_a_switch_to_auto_sends_the_shot_of_now_and_a_switch_to_free_sends_no_more(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: SHOTS)
    now, game, at = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), at.append(now[0]))[0] and ""

    def sleep(s):
        now[0] += s

    switched = []

    def switch(control):                                        # the menu clicks at 5 s (on) and 40 s (off)
        for t in (5000, 40000):
            if control["time"] >= t and t not in switched:
                switched.append(t)
                ri.apply(ri.CAMERA, control)
    replay.Replay(game, data([]), camera=False).run(clock=lambda: now[0], sleep=sleep, log=None, finish=True, poll=switch)
    tps = [(t, c) for t, c in zip(at, game.sent) if "tp @s" in c and "gamemode=spectator" in c]
    assert switched == [5000, 40000]
    assert [c.split()[6] for _, c in tps] == ["22.0", "44.0"]    # the x of tile 5 and of tile 10.5 (4 blocks a tile)
    assert 5.0 <= tps[0][0] < 6.0                               # at the click, not at the shot of 2 s
