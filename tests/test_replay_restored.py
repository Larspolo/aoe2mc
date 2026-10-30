"""A restored record (#4568): the timeline has game times and the replay clock starts at the restore time."""
import os
import sys
import types
from datetime import timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

import aoe2mc  # noqa: E402

RESTORE = 20 * 60 * 1000


def match(restored):
    """A fake mgz match: one action at 5 s and one chat line at 7 s after the save (mgz adds the restore time to
    the chat, not to the actions)."""
    p = types.SimpleNamespace(number=1)
    act = types.SimpleNamespace(type=types.SimpleNamespace(name="RESIGN"), player=p, payload={}, position=None,
                                timestamp=timedelta(seconds=5))
    chat = types.SimpleNamespace(timestamp=timedelta(seconds=7) + (timedelta(milliseconds=RESTORE) if restored
                                                                   else timedelta()), player=p, message="hi")
    return types.SimpleNamespace(actions=[act], chat=[chat], uptimes=[], restored=restored,
                                 restored_at=timedelta(milliseconds=RESTORE if restored else 0))


def timeline(monkeypatch, tmp_path, restored):
    import mgz.model
    monkeypatch.setattr(mgz.model, "parse_match", lambda f: match(restored))
    (tmp_path / "r.aoe2record").write_bytes(b"")
    return aoe2mc.read_timeline(str(tmp_path / "r.aoe2record"))


def test_read_timeline_gives_game_times_of_a_restored_record(monkeypatch, tmp_path):
    t = timeline(monkeypatch, tmp_path, True)
    assert [(e["kind"], e["time"]) for e in t] == [("restore", RESTORE), ("resign", RESTORE + 5000),
                                                   ("chat", RESTORE + 7000)]


def test_read_timeline_of_a_record_that_is_not_restored(monkeypatch, tmp_path):
    t = timeline(monkeypatch, tmp_path, False)
    assert [(e["kind"], e["time"]) for e in t] == [("resign", 5000), ("chat", 7000)]


def test_replay_clock_starts_at_the_restore_time():
    game = Clock()
    d = data([{"time": RESTORE, "player": None, "kind": "restore"},
              {"time": RESTORE + 5000, "player": 1, "kind": "chat", "text": "t1"}])
    replay.Replay(game, d).run(clock=lambda: game.now, sleep=game.sleep, log=None, bar=True)
    assert game.at["t1"] == 5.0                                      # 5 s after the start, not 20 min
    names = [c.split(" name ")[1] for c in game.sent if " name " in c]
    assert names[0] == '{"text": "20:00 · speed 1×"}'
