"""The live replay follows the new view locks of the recording player (#4771): the source gives each new view once,
and --camera player moves the camera entity to a view of a later part of the record."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import chats  # noqa: E402
from test_replay_live import Writer, read_lines  # noqa: E402

TIMELINE = chats(*range(1000, 80001, 5000))
VIEWS = [{"time": t, "tile": [10.0 + t // 5000, 20.0]} for t in range(2000, 76001, 6000)]


def source(path, clock):
    """A Source with a fake read: the views up to the newest event in the file."""
    s = live.Source(str(path), 5.0, clock=clock, check=1.0, idle=30.0)

    def read(p):
        events = read_lines(p)
        newest = max(e["time"] for e in events)
        s.views = [v for v in VIEWS if v["time"] <= newest]
        return events
    s.read = read
    return s


def test_the_source_gives_the_views_of_the_second_part_once(tmp_path):
    path = tmp_path / "game.aoe2record"
    k = len(TIMELINE) // 2
    path.write_text("".join(json.dumps(e) + "\n" for e in TIMELINE[:k]))
    now = [0.0]
    s = source(path, lambda: now[0])
    s.first()
    early = s.fresh_views()
    with open(path, "a") as f:
        f.writelines(json.dumps(e) + "\n" for e in TIMELINE[k:])
    now[0] = 2.0
    new, _ = s.more()
    later = [e for e in new if e["kind"] == "view"]
    assert later and all(v["time"] > TIMELINE[k - 1]["time"] - 5000 for v in later)
    now[0] = 4.0
    assert [e for e in s.more()[0] if e["kind"] == "view"] == []      # no growth: no view again
    now[0] = 40.0
    rest = [e for e in s.more()[0] if e["kind"] == "view"]
    assert [v["time"] for v in early + later + rest] == [v["time"] for v in VIEWS]


def test_camera_player_moves_to_a_view_of_the_second_part(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, "camera_plan", lambda events, owner: [])
    path = tmp_path / "game.aoe2record"
    k = len(TIMELINE) // 2
    path.write_text("".join(json.dumps(e) + "\n" for e in TIMELINE[:k]))
    game = Writer(str(path), [TIMELINE[k:]], [20.0])
    s = source(path, lambda: game.now)
    d = data(s.first())
    d["views"] = [{"time": v["time"], "tile": v["tile"]} for v in s.fresh_views()]
    r = replay.Replay(game, d, camera="player")
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, more=s.more, poll=lambda control: None)
    last = r.shot_place(VIEWS[-1]["tile"])
    assert VIEWS[-1]["time"] > TIMELINE[k - 1]["time"]
    assert any(c == f"tp @e[type=item_display,tag={replay.CAMERA_ENTITY},limit=1] {last}" for c in game.sent)
