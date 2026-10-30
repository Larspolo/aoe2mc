"""The panel of a live replay (#4775): the APM and the town center idle time of a player count the events of each
part of the record, as the replay of the complete record does."""
from test_replay_live import Clock, data, follow, replay

ACTIONS = [{"time": t, "player": 1 + t // 1000 % 2, "kind": "flare", "tile": [8.5, 8.5]} for t in range(1000, 120001, 3000)]
QUEUES = [{"time": t, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"}
          for t in (2000, 40000, 41000, 90000)]
TIMELINE = sorted(ACTIONS + QUEUES, key=lambda e: e["time"])


def test_the_live_apm_counts_the_actions_of_all_parts(tmp_path, monkeypatch):
    flush = replay.Replay.flush
    monkeypatch.setattr(replay.Replay, "flush", lambda self: (self.apm(1, 0), flush(self))[1])   # the panel asks early
    _, r = follow(tmp_path, TIMELINE)
    whole = Clock()
    w = replay.Replay(whole, data([dict(e) for e in TIMELINE]))
    w.run(clock=lambda: whole.now, sleep=whole.sleep, log=None)
    for p in (1, 2):
        for t in (30000, 90000, 120000):
            assert r.apm(p, t) == w.apm(p, t) > 0, (p, t)
            assert r.tc_idle(p, t) == w.tc_idle(p, t), (p, t)
        assert r.mean_apm(p, 120000) == w.mean_apm(p, 120000)
