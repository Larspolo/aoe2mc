"""The live replay follows a record file that AoE2 DE still writes (#4663, epic #4660): a writer adds the record in 4
parts while the replay runs. The replay plays the same events as the replay of the full record, and never an event
later than "newest event time − delay"."""
import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock, chats  # noqa: E402

import aoe2mc  # noqa: E402
import live  # noqa: E402
import replay  # noqa: E402
import run  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")
TIMELINE = chats(*range(1000, 120001, 7000))
DELAY = 10.0


def read_lines(path):
    """The fake record_timeline of a test record: one JSON event per line."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.endswith("\n")]


class Writer(Clock):
    """A fake server and the tool that writes the record: part i goes into the file at real time `when[i]` (s)."""

    def __init__(self, path, parts, when):
        super().__init__()
        self.path, self.parts, self.when, self.newest = path, list(parts), list(when), {}

    def sleep(self, s):
        super().sleep(s)
        while self.when and self.now >= self.when[0]:
            self.when.pop(0)
            with open(self.path, "a") as f:
                f.writelines(json.dumps(e) + "\n" for e in self.parts.pop(0))

    def command(self, cmd):
        out = super().command(cmd)
        for key in set(self.at) - set(self.newest):          # the newest event in the file when the event played
            self.newest[key] = (max(e["time"] for e in read_lines(self.path)), not self.parts)
        return out


def follow(tmp_path, timeline=TIMELINE, when=(20.0, 40.0, 60.0)):
    path = tmp_path / "game.aoe2record"
    k = len(timeline) // 4
    parts = [timeline[:k], timeline[k:2 * k], timeline[2 * k:3 * k], timeline[3 * k:]]
    game = Writer(str(path), parts[1:], when)
    path.write_text("".join(json.dumps(e) + "\n" for e in parts[0]))
    source = live.Source(str(path), DELAY, read=read_lines, clock=lambda: game.now, check=1.0, idle=30.0)
    r = replay.Replay(game, data(source.first()))
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, more=source.more, poll=lambda control: None)
    return game, r


def test_the_live_replay_plays_the_events_of_the_full_record(tmp_path):
    game, r = follow(tmp_path)
    whole = Clock()
    replay.Replay(whole, data([dict(e) for e in TIMELINE])).run(clock=lambda: whole.now, sleep=whole.sleep, log=None)
    assert sorted(game.at) == sorted(whole.at)
    assert r.data["timeline"] == TIMELINE


def test_the_live_replay_stays_the_delay_behind(tmp_path):
    game, _ = follow(tmp_path)
    for key, (newest, complete) in game.newest.items():
        assert complete or int(key[1:]) <= newest - DELAY * 1000, key


def test_the_source_gives_each_event_once_in_order(tmp_path):
    path = tmp_path / "game.aoe2record"
    path.write_text("".join(json.dumps(e) + "\n" for e in TIMELINE[:5]))
    now = [0.0]
    source = live.Source(str(path), DELAY, read=read_lines, clock=lambda: now[0], check=1.0, idle=30.0)
    got = source.first()
    assert got and max(e["time"] for e in got) <= TIMELINE[4]["time"] - DELAY * 1000
    assert source.more() == ([], False)                       # before the next check: no read
    with open(path, "a") as f:
        f.writelines(json.dumps(e) + "\n" for e in TIMELINE[5:])
    now[0] = 2.0
    new, complete = source.more()
    got += new
    assert not complete and max(e["time"] for e in got) <= TIMELINE[-1]["time"] - DELAY * 1000
    now[0] = 40.0                                             # no growth for `idle` seconds: the game ended
    new, complete = source.more()
    assert complete and got + new == TIMELINE


def test_live_errors(tmp_path):
    assert "does not exist" in run.live_error(str(tmp_path), str(tmp_path / "none.aoe2record"))
    rec = tmp_path / "game.aoe2record"
    rec.write_bytes(b"")
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"objects": []}))
    err = run.live_error(str(tmp_path), str(rec))
    assert "\n" not in err and "recorded game" in err
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"timeline": []}))
    assert run.live_error(str(tmp_path), str(rec)) is None
    with pytest.raises(OSError):
        live.Source(str(tmp_path / "none.aoe2record"))


def test_help_names_live_and_delay():
    out = subprocess.run([sys.executable, os.path.join(ROOT, "game", "run.py"), "--help"], capture_output=True,
                         text=True, check=True).stdout
    assert "--live" in out and "--delay" in out
    assert "--live" in run.__doc__ and "--delay" in run.__doc__


@pytest.mark.slow
def test_a_real_record_in_4_parts(tmp_path):
    """The source reads a real record that grows in 4 parts: the events that it gives are those of the full record."""
    whole = aoe2mc.record_timeline(REC)
    path = tmp_path / "game.aoe2record"
    with open(REC, "rb") as f:
        body = f.read()
    path.write_bytes(body[:len(body) // 4])
    now = [0.0]
    source = live.Source(str(path), DELAY, clock=lambda: now[0], check=1.0, idle=30.0)
    got = source.first()
    for i in (2, 3, 4):
        with open(path, "ab") as f:
            f.write(body[len(body) * (i - 1) // 4:len(body) * i // 4])
        now[0] += 2.0
        new, complete = source.more()
        assert complete == (i == 4)                     # the full record has its resign: complete (#4664)
        assert complete or all(e["time"] <= source.events[-1]["time"] - DELAY * 1000 for e in new)
        got += new
    now[0] += 60.0
    new, complete = source.more()
    assert complete and [plain(e) for e in got + new] == [plain(e) for e in whole]


def plain(e):
    """An event without the names that name_timeline guesses from later commands: a part of a record can guess
    another name for an object (#4663), the time, kind, objects and tiles stay."""
    return {k: v for k, v in e.items() if k not in ("names", "target_name")}
