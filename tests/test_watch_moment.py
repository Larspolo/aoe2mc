"""The question of a guided replay check comes WATCH seconds of game time after the moment (game/watch.py, #1123)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import watch  # noqa: E402
from test_watch import Game, chop_replay, drive  # noqa: E402


def test_the_question_comes_30_game_seconds_after_the_moment_at_speed_1():
    game, now, lines, answers = Game(), [0.0, 0.0], [], []
    stages = watch.stages('[{"at": "1:00", "where": "chopper", "what": "a chop", "ask": "Good?"}]')
    g = watch.Guide(game, stages, 4.0, answers, clock=lambda: now[0], log=lines.append)
    g.r = chop_replay()
    control = {"speed": 4.0, "paused": False}
    drive(g, control, game, now, 20, until=lambda: control["paused"])
    drive(g, control, game, now, 30, at={0: "join"}, until=lambda: not control["paused"])
    assert g.state == "watch" and control["speed"] == 1.0
    drive(g, control, game, now, 90, until=lambda: control["paused"])
    assert lines[-1] == "ASK 1"
    assert 60000 + 30000 - 1000 <= now[1] <= 60000 + 30000 + 1000      # 30 s after the moment, not 15 s
