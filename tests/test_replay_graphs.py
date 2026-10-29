"""Live replay: the graphs of each player in the sky above the overview (#3448, decision #3447: B). Fake RCON."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stats import UNITS  # noqa: E402


def game():
    d = data([])
    d["objects"] = UNITS
    return replay.Replay(Fake(), d)


def rows(cmd):
    """The text components of a summon or data merge command of the graphs."""
    return json.loads(cmd[cmd.index("text:") + 5:].split(",billboard")[0].removesuffix("}"))


def test_the_graphs_change_each_minute_and_only_then():
    r = game()
    r.sample(0)
    first = r.graphs(0)
    assert len(first) == 4 and all(c.startswith("summon text_display") for c in first)   # one per value
    lines = rows(first[0])
    assert [x["text"] for x in lines[:1]] == ["Population\n"] and len(lines) == 3          # the title, 2 players
    assert [x["color"] for x in lines[1:]] == [r.label(1)[1], r.label(2)[1]]
    r.pop[1] += 3
    r.sample(30000)
    assert r.graphs(30000) == []                                # the same minute: no command
    r.sample(61000)
    second = r.graphs(61000)
    assert len(second) == 4 and all(c.startswith("data merge entity @e[type=text_display") for c in second)
    assert f"tag={replay.GRAPH}.1," in second[0]                                            # a new bar in each
    assert rows(second[0])[1]["text"] == f"{r.label(1)[0]} ▃█ 4\n"


def test_a_jump_shows_the_values_of_the_new_time():
    r = game()
    r.sample(0)
    r.graphs(0)
    r.villager(1, 5)
    r.sample(185000)                                            # a jump from 0:00 to 3:05
    jump = r.graphs(185000)
    assert len(jump) == 4 and f"tag={replay.GRAPH}.2," in jump[1]
    assert rows(jump[1])[1]["text"] == f"{r.label(1)[0]} ▂███ 6\n"                       # minutes 0 to 3


@pytest.mark.mc
def test_the_graph_commands_run_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    r = game()
    r.sample(0)
    with run.Game(world) as g:
        g.command("forceload add 0 0 63 63")
        for t in (0, 61000):
            r.pop[1] += 2
            r.sample(t)
            cmds = r.graphs(t)
            assert cmds
            for c in cmds:
                out = g.command(c)
                assert not any(w in out for w in ("Unknown", "Incorrect", "Expected", "No entity")), (c, out)
        out = g.command(f"data get entity @e[type=text_display,tag={replay.GRAPH}.1,limit=1] text")
        assert "Britons" in out, out


def test_each_graph_command_of_8_players_stays_below_the_rcon_limit():
    from test_replay_eight_players import eight
    import rcon
    r = replay.Replay(Fake(), eight([]))
    for p in range(1, 9):
        r.pop[p] = 199 - p
        r.gathered[p] = {"food": 99999}
    r.sample(45 * 60000)
    cmds = r.graphs(45 * 60000)
    assert len(cmds) == 4 and max(len(c.encode()) for c in cmds) <= rcon.MAX
    assert len(rows(cmds[0])) == 9 and all(x["text"].count("█") + x["text"].count("▁") >= 20 for x in rows(cmds[0])[1:])
