"""The graphs of the live replay with a recorded game: the samples and the graph commands at 5:00 and 10:00 (#3748,
epic #3445). The game plays in real time to 10:00 with a fake clock: no hand-made samples. The villagers equal the
VILLAGER_MALE trains that end by that time (aoe2mc.training of the record: 11 and 10 at 5:00, 19 and 17 at 10:00)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import aoe2mc  # noqa: E402
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

REC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples", "de-64.3.aoe2record")
END = 10 * 60000


def play_to_ten():
    timeline = [e for e in aoe2mc.read_timeline(REC) if e["time"] <= END]
    d = data(timeline + [dict(time=END + 1000, player=1, kind="chat", text="end")], n=480)
    d["objects"] = [dict(o, tile=[o["x"], o["y"]]) for o in aoe2mc.read_record(REC)[5]]   # the tile of the converter
    d["players"]["2"]["arch"] = "western"       # data() has "meso", which buildings.ARCH lacks
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None)
    return r


def test_the_samples_of_two_players_at_five_and_ten_minutes():
    r = play_to_ten()
    five, ten = r.stats(5 * 60000), r.stats(END)
    assert sorted(five) == [1, 2] and sorted(ten) == [1, 2]
    assert [len(five[p]) for p in (1, 2)] == [5, 5] and [len(ten[p]) for p in (1, 2)] == [10, 10]   # minutes 1 to 5, 1 to 10
    assert [s[2] for s in five[1]][-1] == 11 and [s[2] for s in five[2]][-1] == 10
    assert [s[2] for s in ten[1]][-1] == 19 and [s[2] for s in ten[2]][-1] == 17
    for p in (1, 2):
        assert all(s[1] >= s[2] for s in ten[p])            # the population covers the villagers


def rows(cmd):
    """The text components of a summon or data merge command of the graphs."""
    return json.loads(cmd[cmd.index("text:") + 5:].split(",billboard")[0].removesuffix("}"))


def test_the_graphs_at_ten_minutes_have_a_row_per_player_and_a_bar_per_minute():
    r = play_to_ten()
    r.graph = {}                                            # the play sent the graphs already: a new view
    cmds = r.graphs(END)
    assert len(cmds) == 4
    for cmd in cmds:
        lines = rows(cmd)
        assert len(lines) == 3                              # the title and the two players
        assert all(len(x["text"].split(" ")[-2]) == 10 for x in lines[1:])   # one bar per game minute, 1 to 10
