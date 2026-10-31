"""--camera player over the view locks of the real DE sample records (#5011, criteria 1 and 2 of #4765): at each time
the last camera move is at the last view of the recorder before it, also after a jump back, a pause and a speed change."""
import bisect
import os
import sys

import pytest

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = ["de-63.0", "de-64.3"]
CACHE = {}


def views(name):
    if name not in CACHE:
        state = {}
        aoe2mc.read_timeline(os.path.join(ROOT, "samples", f"{name}.aoe2record"), state)
        CACHE[name] = state["views"]
    return CACHE[name]


def place(c):
    """The place of a camera move (#4768, #4770), or None."""
    if c.startswith("tp @e[type=item_display") or ("tp @s" in c and "gamemode=spectator" in c):
        return c.split(" tp ")[-1].split(maxsplit=2)[-1] if c.startswith("execute") else c.split(maxsplit=2)[2]
    return None


def play(vs, control=lambda c: None, start=0, rewind=False, speed=8.0):
    """Run the replay with the views vs; at each poll, check that the last camera move is at the last view before
    the game time. Gives (the checked polls, the stats)."""
    now, game, last, checked = [0.0], Fake(), [None], [0]
    r = replay.Replay(game, data([]) | {"views": vs, "recorder": 1}, camera="player")
    times = [v["time"] for v in vs]
    game.command = lambda c: (game.sent.append(c), (p := place(c)) and last.__setitem__(0, p), None)[2]

    def poll(c):
        k = bisect.bisect_left(times, c["time"] - 1) - 1               # the last view before now
        ok = {r.shot_place(vs[j]["tile"]) for j in range(k, bisect.bisect_right(times, c["time"] + 1)) if j >= 0}
        if k >= 0 and c["time"] - start > 1:   # or a view at now: it can go before this poll
            assert last[0] in ok, (c["time"], times[k])
            checked[0] += 1
        control(c)
    stats = r.run(speed, start=start, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), log=None,
                  finish=True, poll=poll, rewind=rewind)
    return checked[0], stats


@pytest.fixture(autouse=True)
def no_plan(monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])


@pytest.mark.parametrize("name", RECORDS)
def test_the_camera_follows_each_view_of_the_recorder(name):
    vs = views(name)
    checked, _ = play(vs)
    assert len(vs) > 10 and checked > len(vs)


@pytest.mark.parametrize("name", RECORDS)
def test_pause_speed_and_jump_back_keep_the_camera_at_the_last_view(name):
    vs = views(name)
    mid, steps = vs[len(vs) // 2]["time"], []

    def control(c):
        if c["time"] >= mid / 4 and "pause" not in steps:
            steps.append("pause")
            c["paused"] = True
        elif "pause" in steps and "go" not in steps:
            if len(steps) < 6:
                steps.append("wait")
            else:
                steps.append("go")
                c["paused"], c["speed"] = False, 20.0
        elif c["time"] >= mid and "back" not in steps:
            steps.append("back")
            c["jump"] = mid / 2
    checked, stats = play(vs, control, rewind=True)
    assert "go" in steps and stats["rewind"] == mid / 2 and checked
    checked, _ = play(vs, start=stats["rewind"])                     # the fresh replay after the jump back (#979)
    assert checked
