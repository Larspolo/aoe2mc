"""The live replay ends when the game of AoE2 DE ends (#4664, epic #4660): at the resign of the record (mgz
match.completed) with the same end as the replay of the complete record, or when the file does not grow for a set time,
with one line that says why."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_replay import data  # noqa: E402
from test_replay_control import Clock, chats  # noqa: E402

import aoe2mc  # noqa: E402
import live  # noqa: E402
import replay  # noqa: E402

TIMELINE = chats(*range(1000, 60001, 7000)) + [{"time": 61000, "player": 2, "kind": "resign"}]
IDLE = 300.0                        # longer than the whole test: only the record end can stop the replay


def end(sent):
    """The commands after the last chat event: the end title, the summary and the books."""
    k = max(i for i, c in enumerate(sent) if c.startswith("tellraw") and '"t' in c and "Summary" not in c)
    return [c for c in sent[k + 1:] if not c.startswith(("bossbar", "title @a actionbar"))]


def follow(tmp_path, parts, when, ended, idle=IDLE):
    """A replay of a record that a fake writer adds in parts (part i at real time when[i]); ended(lines): the record
    has the end of the game (match.completed of mgz)."""
    path = tmp_path / "game.aoe2record"
    path.write_text("".join(json.dumps(e) + "\n" for e in parts[0]))
    rest, times, logs = list(parts[1:]), list(when), []
    game = Clock()
    sleep = game.sleep

    def write(s):
        sleep(s)
        while times and game.now >= times[0]:
            times.pop(0)
            with open(path, "a") as f:
                f.writelines(json.dumps(e) + "\n" for e in rest.pop(0))
    game.sleep = write

    def read(p):
        with open(p) as f:
            lines = [json.loads(line) for line in f]
        source.ended = ended(lines)
        return lines
    source = live.Source(str(path), 5.0, read=read, clock=lambda: game.now, check=1.0, idle=idle, log=logs.append)
    r = replay.Replay(game, data(source.first()))
    stats = r.run(bar=True, clock=lambda: game.now, sleep=game.sleep, log=None, more=source.more, poll=lambda control: None)
    return game, stats, logs


def test_a_record_that_becomes_complete_ends_with_the_end_of_the_complete_record(tmp_path):
    k = len(TIMELINE) // 2
    game, stats, logs = follow(tmp_path, [TIMELINE[:k], TIMELINE[k:]], [20.0],
                               lambda lines: lines[-1]["kind"] == "resign")
    whole = Clock()
    replay.Replay(whole, data([dict(e) for e in TIMELINE])).run(bar=True, clock=lambda: whole.now, sleep=whole.sleep, log=None)
    assert game.now < IDLE                                   # the end of the record, not the idle time
    assert sorted(game.at) == sorted(whole.at)
    assert end(game.sent) == end(whole.sent)
    assert any("Replay ended" in c for c in end(game.sent)) and any("Summary" in c for c in end(game.sent))
    assert len(logs) == 1 and "complete" in logs[0]


def test_a_record_that_does_not_grow_ends_after_the_idle_time_with_one_line(tmp_path):
    game, stats, logs = follow(tmp_path, [TIMELINE[:4]], [], lambda lines: False, idle=30.0)
    assert 30.0 <= game.now < IDLE
    assert any("Replay ended" in c for c in end(game.sent))
    assert len(logs) == 1 and "30 s" in logs[0] and "\n" not in logs[0]


def test_the_source_reads_the_end_flag_of_the_record(tmp_path, monkeypatch):
    path = tmp_path / "game.aoe2record"
    path.write_bytes(b"x")

    def timeline(src, turn=0, state=None):
        state["complete"] = True
        return chats(1000)
    monkeypatch.setattr(aoe2mc, "record_timeline", timeline)
    source = live.Source(str(path), 5.0, clock=lambda: 0.0, check=0.0, idle=IDLE, log=lambda m: None)
    assert source.first() == [] and source.ended
    assert source.more() == (chats(1000), True)
