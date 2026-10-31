"""tools/replay_shot.py (#5273): the arguments and the time plan of the screenshots of a live replay, without a client."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import replay_shot  # noqa: E402


def test_the_plan_sorts_the_times_and_names_one_png_each():
    shots = replay_shot.plan("out/shot.png", ["0:31", "0:11", "0:11", "1:05"])
    assert shots == [(11000, "out/shot_0m11s.png"), (31000, "out/shot_0m31s.png"), (65000, "out/shot_1m05s.png")]


def test_the_poll_takes_the_shots_whose_time_came():
    shots = replay_shot.plan("s", ["0:10", "0:30"])
    assert replay_shot.due(shots, 9999) == [] and replay_shot.due(shots, 10000) == shots[:1]
    assert replay_shot.due(shots, 40000) == shots


def test_the_arguments_need_a_time_and_read_the_view(monkeypatch):
    with pytest.raises(SystemExit):
        replay_shot.main(["rec.aoe2record", "o.png"])
    seen = {}
    monkeypatch.setattr(replay_shot, "run_shots", lambda *a: seen.setdefault("a", a) and [])
    replay_shot.main(["rec.aoe2record", "o.png", "--at-time", "0:11", "--view", "138,70,150,180,30", "--speed", "2"])
    assert seen["a"] == ("rec.aoe2record", "o.png", ["0:11"], (138.0, 70.0, 150.0, 180.0, 30.0), 2.0, None)
