"""The live replay keeps running while AoE2 DE is paused (#4951): AoE2 DE writes nothing while the game is paused, so
the source logs one line after PAUSE s with no growth and keeps the record open until IDLE s (or the record end)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import live  # noqa: E402


def test_a_pause_of_120_s_waits_with_one_line_and_then_gives_the_new_events(tmp_path):
    path = tmp_path / "game.aoe2record"
    path.write_bytes(b"x" * 10)
    now, logs, content = [0.0], [], [{"time": 1000}]
    source = live.Source(str(path), delay=0, read=lambda p: list(content), clock=lambda: now[0], check=1.0,
                         log=logs.append)
    assert [e["time"] for e in source.first()] == [1000]
    for t in (60.0, 62.0, 90.0, 120.0):                  # no growth: the pause line once, the record stays open
        now[0] = t
        assert source.more() == ([], False)
    assert len(logs) == 1 and "60 s" in logs[0] and "waits" in logs[0] and "\n" not in logs[0]
    content.append({"time": 2000})                       # the game goes on: the new event, not complete
    path.write_bytes(b"x" * 20)
    now[0] = 122.0
    events, complete = source.more()
    assert [e["time"] for e in events] == [2000] and not complete
    assert len(logs) == 1


def test_a_second_pause_logs_its_own_line(tmp_path):
    path = tmp_path / "game.aoe2record"
    path.write_bytes(b"x" * 10)
    now, logs = [0.0], []
    source = live.Source(str(path), delay=0, read=lambda p: [{"time": 1000}], clock=lambda: now[0], check=1.0,
                         log=logs.append)
    source.first()
    now[0] = 70.0
    source.more()
    path.write_bytes(b"x" * 20)
    now[0] = 80.0
    source.more()                                         # growth at 80 s: the next pause may log again
    now[0] = 150.0
    source.more()
    assert sum("waits" in m for m in logs) == 2


def test_no_growth_for_idle_time_ends_the_replay_with_one_line(tmp_path):
    path = tmp_path / "game.aoe2record"
    path.write_bytes(b"x" * 10)
    now, logs = [0.0], []
    source = live.Source(str(path), delay=0, read=lambda p: [{"time": 1000}], clock=lambda: now[0], check=1.0,
                         log=logs.append)
    source.first()
    now[0] = 599.0
    assert source.more()[1] is False
    now[0] = 600.0
    events, complete = source.more()
    assert complete and events == []
    assert logs[-1] == "live: the record did not grow for 600 s: the game ended"
    assert len(logs) == 2                                 # the pause line, then the idle line
