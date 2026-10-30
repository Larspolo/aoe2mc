"""The army rows of the live replay with a recorded game (#3843, criterion 2 of #3693). The game plays in real time to
15:00 and 20:00 with a fake clock. A fake census answers the live count of each type; after 16:00 one ARCHER of player 2
dies in a fight, which has no timeline event (#787): only the census finds it."""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_stat_books import page  # noqa: E402

import aoe2mc  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
FIGHT = 16 * 60                                         # game seconds (speed 1): one archer of player 2 dies after it


class Census(Clock):
    """The fake clock, and a census that counts the units of the replay itself, less one dead ARCHER of player 2."""
    r, died = None, False

    def command(self, cmd):
        out = super().command(cmd)
        if not cmd.startswith("execute if entity") or "type=" in cmd:     # the villager count: no answer
            return out
        p = int(re.search(r"aoe2mc\.p(\d+)", cmd)[1])
        if not (m := re.search(r"aoe2mc\.t(\d+)", cmd)):
            return f"Test passed, Count: {self.r.pop[p]}"
        name = next(n for n in self.r.troops[p] if str(replay.units.type_ids().get(n)) == m[1])
        n = self.r.troops[p][name]
        if (p, name) == (2, "ARCHER") and self.now >= FIGHT and not self.died:
            self.died, n = True, n - 1
        return f"Test passed, Count: {n}"


def play_to(minutes):
    end = minutes * 60000
    timeline = [e for e in aoe2mc.read_timeline(REC) if e["time"] <= end]
    d = data(timeline + [dict(time=end + 1000, player=1, kind="chat", text="end")], n=480)
    d["objects"] = [dict(o, tile=[o["x"], o["y"]]) for o in aoe2mc.read_record(REC)[5]]   # the tile of the converter
    d["players"]["2"]["arch"] = "western"       # data() has "meso", which buildings.ARCH lacks
    game = Census()
    game.r = r = replay.Replay(game, d, ai=True)          # ai and bar: the census of run.py --replay
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, bar=True)
    trained = collections.Counter((e["player"], e["name"]) for done, e, _ in r.trainings
                                  if e["kind"] == "queue" and done <= end and gather.military(e["name"]))
    r.books = {}                                        # a new view: the whole book
    cmds = r.army_view(end)
    rows = {p: (lines := page(cmds, k))[:lines.index("")] for k, p in enumerate((1, 2))}   # the army lines
    return r, trained, rows


def counts(row):
    """The military types and counts of the army lines of a page: ["Army: 3 Scout Cavalry", "Lost: 1"]."""
    army = row[0].split(": ", 1)[1]
    return {} if army == "-" else {w.split(" ", 1)[1]: int(w.split(" ", 1)[0]) for w in army.split(", ")}


def test_the_army_rows_of_two_players_at_15_and_20_minutes_follow_the_record_and_the_census():
    for minutes in (15, 20):
        r, trained, rows = play_to(minutes)
        assert sorted(rows) == [1, 2]
        for p in (1, 2):
            want = {replay.pretty(n): c - r.fallen.get(p, {}).get(n, 0) for (q, n), c in trained.items() if q == p}
            assert want and counts(rows[p]) == {n: c for n, c in want.items() if c}
        if minutes == 15:
            assert r.fallen == {} and not [x for x in rows[2] if x.startswith("Lost")]
            assert "Scout Cavalry" in counts(rows[1]) and "Eagle Scout" in counts(rows[2])
        else:
            assert r.fallen == {2: {"ARCHER": 1}} and "Lost: 1" in rows[2]
            assert counts(rows[2])["Archer"] == trained[2, "ARCHER"] - 1 >= 1
