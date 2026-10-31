"""Live replay: the camera of --camera player is a display entity that glides from view to view (#4770). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import re  # noqa: E402

import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

VIEWS = [{"time": 2000, "tile": [5, 6]}, {"time": 2400, "tile": [10.5, 3]}, {"time": 12000, "tile": [2, 9.5]}]
CAM = f"@e[type=item_display,tag={replay.CAMERA_ENTITY},limit=1]"


def run(views, speed=1.0, n=64):
    now, game = [0.0], Fake()
    replay.Replay(game, data([], n=n) | {"views": views, "recorder": 1}, camera="player").run(
        speed=speed, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True)
    return game.sent


def durations(sent):
    """The teleport_duration of the camera entity at each of its tp."""
    out, d = [], None
    for c in sent:
        if m := re.search(r"teleport_duration:(\d+)", c):
            d = int(m[1])
        if c.startswith(f"tp {CAM} "):
            out.append(d)
    return out


def place(tile, n=64):
    return replay.Replay(Fake(), data([], n=n)).shot_place(tile)


def test_each_view_is_one_tp_of_the_camera_entity_not_of_the_spectators(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    sent = run(VIEWS)
    assert [c for c in sent if c.startswith(f"tp {CAM} ")] == [f"tp {CAM} {place(v['tile'])}" for v in VIEWS]
    assert [c for c in sent if "run tp @s" in c] == [f"execute as @a[gamemode=spectator] run tp @s {place([5, 6])}"]
    assert sum(c.startswith("summon item_display") and replay.CAMERA_ENTITY in c for c in sent) == 1
    assert sum(f"run spectate {CAM} @s" in c for c in sent) == 2     # the first view, again after CAMERA_MS
    assert all(1 <= d <= 59 for d in durations(sent))


def test_a_far_view_jumps_with_a_new_camera_entity(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    far = [{"time": 2000, "tile": [5, 6]}, {"time": 4000, "tile": [5 + replay.JUMP / 4 + 2, 6]}]
    sent = run(far, n=256)
    assert [c for c in sent if "run tp @s" in c] == [f"execute as @a[gamemode=spectator] run tp @s {place(v['tile'], 256)}"
                                                     for v in far]
    assert sum(c.startswith("summon item_display") for c in sent) == 2
    assert sum(f"run spectate {CAM} @s" in c for c in sent) == 2


def test_the_glide_ends_before_the_next_view_and_is_shorter_at_a_higher_speed(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    assert durations(run(VIEWS)) == [8, replay.GLIDE, replay.GLIDE]       # 400 ms to the next view: 8 ticks
    assert durations(run(VIEWS, speed=8)) == [1, 20, replay.GLIDE]        # 9600 ms / 8: 24 ticks, at most GLIDE


def test_the_end_of_the_replay_kills_the_camera_entity(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    sent = run(VIEWS)
    last_tp = max(i for i, c in enumerate(sent) if c.startswith(f"tp {CAM} "))
    assert any(c == f"kill @e[type=item_display,tag={replay.CAMERA_ENTITY}]" for c in sent[last_tp:])


def test_the_camera_menu_ends_the_player_camera(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    now, game, marks = [0.0], Fake(), []

    def poll(control):
        if control["time"] >= 3000 and len(marks) < 2:
            marks.append(len(game.sent))                            # the switch and the next poll
            control["camera"] = "auto"
    replay.Replay(game, data([]) | {"views": VIEWS, "recorder": 1}, camera="player").run(
        clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None, finish=True, poll=poll)
    assert f"kill @e[type=item_display,tag={replay.CAMERA_ENTITY}]" in game.sent[marks[0]:marks[1]]
    assert [c for c in game.sent[marks[0]:] if c.startswith(f"tp {CAM} ")] == []
