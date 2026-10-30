"""Live replay: --camera player moves the spectators to the views of the recording player (#4768). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

VIEWS = [{"time": 2000, "tile": [5, 6]}, {"time": 6000, "tile": [10.5, 3]}, {"time": 12000, "tile": [2, 9.5]}]


def spectator_tps(commands):
    return [c for c in commands if "tp @s" in c and "gamemode=spectator" in c]


def shot(tile):
    return replay.Replay(Fake(), data([])).shot_view(tile)[0]


def run(views, camera="player", jump=None):
    now, game, jumped = [0.0], Fake(), []
    game.command = lambda c: (game.sent.append(c), None)[1]
    d = data([]) | ({"views": views, "recorder": 1} if views else {})

    def poll(control):
        if jump is not None and control["time"] >= 1000 and not jumped:
            jumped.append(True)
            control["jump"] = jump
    replay.Replay(game, d, camera=camera).run(clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s),
                                              log=None, finish=True, poll=poll)
    return game.sent


def test_each_view_moves_the_spectators_above_its_tile(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    assert spectator_tps(run(VIEWS)) == [shot(v["tile"]) for v in VIEWS]


def test_a_jump_forward_moves_the_camera_to_the_last_view_before_it(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    assert spectator_tps(run(VIEWS, jump=8000)) == [shot([10.5, 3]), shot([2, 9.5])]


def test_views_move_nothing_with_the_auto_camera(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    assert spectator_tps(run(VIEWS, camera="auto")) == []


def test_a_record_with_no_views_says_so_and_keeps_the_free_camera(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    sent = run([])
    assert any("no camera of its player" in c for c in sent) and spectator_tps(sent) == []
