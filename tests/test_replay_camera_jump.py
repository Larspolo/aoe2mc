"""Live replay: a jump in time keeps --camera auto and moves the spectators to the shot of the new time (#3368). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

THREE = [{"time": 2000, "tile": [5, 6], "why": "build"}, {"time": 6000, "tile": [10.5, 3], "why": "build"},
         {"time": 12000, "tile": [2, 9.5], "why": "fight"}]
LATE = [{"time": 2000, "tile": [5, 6], "why": "build"}, {"time": 30000, "tile": [10.5, 3], "why": "fight"}]


def spectator_tps(commands):
    return [c for c in commands if "tp @s" in c and "gamemode=spectator" in c]


def shot(tile):
    return replay.Replay(Fake(), data([]), camera=True).shot_view(tile)[0]


def clock_and_sleep(now):
    return (lambda: now[0]), (lambda s: now.__setitem__(0, now[0] + s))


def test_a_jump_over_three_shots_sends_one_tp_to_the_third(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: THREE)
    now, game, jumped = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), None)[1]

    def poll(control):                                          # a jump over all three shots, at 1 s of the replay
        if control["time"] >= 1000 and not jumped:
            jumped.append(True)
            control["jump"] = 15000

    clock, sleep = clock_and_sleep(now)
    replay.Replay(game, data([]), camera=True).run(clock=clock, sleep=sleep, log=None, finish=True, poll=poll)
    assert jumped and spectator_tps(game.sent) == [shot([2, 9.5])]


def test_a_jump_back_keeps_the_camera_and_moves_it_to_the_shot_of_the_time(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: LATE)
    now, game, jumped = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), None)[1]

    def poll(control):                                          # at 20 s, a jump back to 5 s
        if control["time"] >= 20000 and not jumped:
            jumped.append(True)
            control["jump"] = 5000

    clock, sleep = clock_and_sleep(now)
    replay.live(lambda: replay.Replay(game, data([]), camera=True), restart=lambda: game.sent.append("RESTART"),
                clock=clock, sleep=sleep, log=None, finish=True, poll=poll)
    after = game.sent[game.sent.index("RESTART") + 1:]
    assert jumped and spectator_tps(after) == [shot([5, 6]), shot([10.5, 3])]
