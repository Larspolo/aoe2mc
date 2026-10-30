"""Live replay: the CAMERA button cycles free, auto and player; the player camera needs views (#4769). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
import replay_input as ri  # noqa: E402
from test_replay import Fake, data  # noqa: E402

VIEWS = [{"time": 2000, "tile": [5, 6]}, {"time": 9000, "tile": [10.5, 3]}]


def press(control, n=1):
    return [ri.apply(ri.CAMERA, control) for _ in range(n)]


def test_three_presses_go_auto_player_free_with_views():
    control = {"camera": None, "views": True}
    assert press(control, 3) == ["Camera: auto", "Camera: player", "Camera: free"]


def test_two_presses_go_auto_free_without_views():
    control = {"camera": None, "views": False}
    assert press(control, 2) == ["Camera: auto", "Camera: free"]


def test_the_switch_to_player_sends_the_view_above_the_last_view_before_now():
    now, game, at = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), at.append(now[0]))[0] and ""
    pressed = []

    def switch(control):                                        # the menu clicks CAMERA at 5 s (auto) and 6 s (player)
        for t in (5000, 6000):
            if control["time"] >= t and t not in pressed:
                pressed.append(t)
                ri.apply(ri.CAMERA, control)

    def sleep(s):
        now[0] += s

    d = data([]) | {"views": VIEWS, "recorder": 1}
    replay.Replay(game, d, camera=False).run(clock=lambda: now[0], sleep=sleep, log=None, finish=True, poll=switch)
    tps = [c for t, c in zip(at, game.sent) if "tp @s" in c and "gamemode=spectator" in c and 6.0 <= t < 9.0]
    assert pressed == [5000, 6000]
    assert tps == [replay.Replay(Fake(), data([])).shot_view(VIEWS[0]["tile"])[0]]
