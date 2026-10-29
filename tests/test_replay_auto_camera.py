"""Live replay: --camera auto moves the spectators to each shot of the camera plan (#3367). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
import run  # noqa: E402
from test_replay import Fake, data  # noqa: E402

SHOTS = [{"time": 2000, "tile": [5, 6], "why": "build"}, {"time": 30000, "tile": [10.5, 3], "why": "fight"}]


def play(monkeypatch, camera):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: SHOTS)
    now, game, at = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), at.append(now[0]))[0] and ""

    def sleep(s):
        now[0] += s
    replay.Replay(game, data([]), camera=camera).run(clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return [(t, c) for t, c in zip(at, game.sent) if "tp @s" in c and "gamemode=spectator" in c]


def test_each_shot_moves_the_spectators_at_its_time(monkeypatch):
    up, back = replay.CAMERA_UP, replay.CAMERA_BACK
    assert play(monkeypatch, True) == [
        (pytest.approx(2.0), f"execute as @a[gamemode=spectator] run tp @s 22.0 {70 + up} {26.0 + back} 180 45.0"),
        (pytest.approx(30.0), f"execute as @a[gamemode=spectator] run tp @s 44.0 {70 + up} {14.0 + back} 180 45.0")]


def test_no_camera_tp_without_the_option(monkeypatch):
    assert play(monkeypatch, False) == []


def test_camera_auto_and_follow_stop_with_a_message(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--replay", "--camera", "auto", "--follow", "1"])
    assert "give only one of them" in capsys.readouterr().err
