"""The heat map of a kind and a time range on demand in the replay (#5589): /trigger aoe_replay set N."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import heatmap  # noqa: E402
import replay  # noqa: E402
import replay_input  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def tiles(cmds):
    return {tuple(int(v) for v in t.split(",")[:2]) for c in cmds for t in c.split()[4:] if t != "end"}


def moves():
    return [{"time": 30000, "player": 1, "kind": "move", "tile": [2, 3]},
            {"time": 150000, "player": 2, "kind": "move", "tile": [5, 6]},
            {"time": 160000, "player": 1, "kind": "attack_move", "tile": [7, 7]}]


class Deaths(Fake):
    def __init__(self, answers):
        super().__init__()
        self.answers = answers

    def command(self, cmd):
        self.sent.append(cmd)
        return self.answers.pop(0) if cmd.startswith("aoe deathmarks heat") else ""


def test_the_trigger_value_gives_kind_and_range():
    for kind in replay_input.HEAT_KINDS:
        control = {}
        assert replay_input.apply(replay_input.heat_value(kind, 2, 5), control)
        assert control["heat"] == (kind, 120000, 300000)
    control = {}
    replay_input.apply(replay_input.heat_value("fight"), control)
    assert control["heat"] == ("fight", 0, None)


def test_walk_and_fight_of_a_range():
    r = replay.Replay(Fake(), data(moves()))
    assert tiles(r.heat_commands("walk", 0, 60000)) == {(2, 3)}
    assert tiles(r.heat_commands("walk", 60000, None)) == {(5, 6), (7, 7)}
    assert tiles(r.heat_commands("fight", 0, None)) == {(7, 7)}


def test_death_range_subtracts_the_start_counts():
    r = replay.Replay(Deaths(["Deaths: p1 1 1 2", "Deaths: p1 1 1 2 p2 4 4 1", "Deaths: p1 1 1 2 p2 4 4 1 p1 3 3 1"]),
                      data([]), ai=True)
    r.death_snapshot(0)
    r.death_snapshot(65000)
    r.death_snapshot(70000)                                  # the same minute: no new query
    assert tiles(r.heat_commands("death", 0, 60000)) == {(1, 1), (4, 4)}
    assert tiles(r.heat_commands("death", 60000, None)) == {(3, 3)}


def test_the_end_gives_the_three_kinds():
    r = replay.Replay(Deaths(["Deaths: p2 4 4 1"]), data(moves()), ai=True)
    cmds = r.end_heat_commands()
    assert sum(c.endswith(" end") for c in cmds) == len(heatmap.KINDS)
    assert tiles(cmds) == {(2, 3), (5, 6), (7, 7), (4, 4)}
