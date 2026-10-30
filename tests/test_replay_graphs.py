"""Live replay: the graphs of each player in the book "Graphs" (#3448, #3924). Fake RCON."""
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_stat_books import page, pages  # noqa: E402
from test_replay_stats import UNITS  # noqa: E402


def game():
    d = data([])
    d["objects"] = UNITS
    return replay.Replay(Fake(), d)


def test_the_graphs_change_each_minute_and_only_then():
    r = game()
    r.sample(0)
    first = r.graphs(0)
    assert len(first) == 1 and first[0].startswith(f"item replace entity @a hotbar.{replay.STAT_BOOKS['Graphs']} ")
    assert [line.split(" ")[0] for line in page(first, 0)] == ["Pop", "Vil", "Mil", "Res"] and len(pages(first)) == 2
    r.pop[1] += 3
    r.sample(30000)
    assert r.graphs(30000) == []                                # the same minute: no command
    r.sample(61000)
    second = r.graphs(61000)
    assert len(second) == 1 and page(second, 0)[0] == "Pop ▒█ 4"                             # a new bar


def test_a_jump_shows_the_values_of_the_new_time():
    r = game()
    r.sample(0)
    r.graphs(0)
    r.villager(1, 5)
    r.sample(185000)                                            # a jump from 0:00 to 3:05
    assert page(r.graphs(185000), 0)[1] == "Vil ░███ 6"                                     # minutes 0 to 3


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
        g.command("summon armor_stand 8 70 8 {Tags:[\"viewer\"]}")
        for t in (0, 61000):
            r.pop[1] += 2
            r.sample(t)
            cmds = [c.replace("@a", "@e[tag=viewer,limit=1]") for c in r.graphs(t)]
            assert cmds
            for c in cmds:
                out = g.command(c)
                assert not any(w in out for w in ("Unknown", "Incorrect", "Expected", "No ")), (c, out)


def test_the_graph_book_of_8_players_stays_below_the_rcon_limit():
    import rcon
    from test_replay_eight_players import eight
    r = replay.Replay(Fake(), eight([]))
    for p in range(1, 9):
        r.pop[p] = 199 - p
        r.gathered[p] = {"food": 99999}
    r.sample(45 * 60000)
    cmds = r.graphs(45 * 60000)
    assert max(len(c.encode()) for c in cmds) <= rcon.MAX
    assert len(pages(cmds)) == 8 and all(len(page(cmds, k)[0].split(" ")[1]) == replay.GRAPH_MINUTES for k in range(8))
