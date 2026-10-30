"""Live replay: the population sidebar shows the age of each player (#805). Fake RCON and a fake clock."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402
from test_replay_score import KNIGHT  # noqa: E402
from test_replay_walk import VIL  # noqa: E402


def chat(t):
    return {"time": t, "player": 1, "kind": "chat", "text": f"t{t}"}


def age(t, player, name):
    return {"time": t, "player": player, "kind": "age", "age": name}


def play(timeline, jump=None):
    d = data(timeline)
    d["objects"] += [VIL, KNIGHT]
    game, done = Clock(), []

    def poll(control):
        if jump and game.now >= jump[0] and not done:
            control["jump"] = jump[1]
            done.append(game.now)
    replay.Replay(game, d).run(clock=lambda: game.now, sleep=game.sleep, log=None, bar=True, poll=poll)
    names = [json.loads(c.split(" ", 6)[6])["text"] for c in game.sent if c.startswith("scoreboard players display name")]
    last, out = {}, []                              # without the resources (#932) and the APM (#3764), per player
    for n in (n.split(" · F ")[0] for n in names):
        if last.get(n.split(" (")[0]) != n:
            out.append(n)
        last[n.split(" (")[0]] = n
    return out


def test_the_sidebar_starts_in_the_dark_age_and_an_age_up_changes_the_line():
    names = play([chat(1000), age(5000, 2, "FEUDAL_AGE"), chat(8000), age(9000, 2, "CASTLE_AGE"), chat(12000)])
    assert names == ["Player 1 (Britons) · Dark", "Player 2 (Aztecs) · Dark", "Player 2 (Aztecs) · Feudal",
                     "Player 2 (Aztecs) · Castle"]


def test_a_jump_shows_the_age_at_the_jump_time():
    names = play([chat(1000), age(30000, 1, "FEUDAL_AGE"), age(50000, 1, "CASTLE_AGE"), age(90000, 1, "IMPERIAL_AGE"),
                  chat(120000)], jump=(5, 60000))
    assert names[:2] == ["Player 1 (Britons) · Dark", "Player 2 (Aztecs) · Dark"]
    assert names[2:] == ["Player 1 (Britons) · Castle", "Player 1 (Britons) · Imperial"]   # Feudal is skipped


@pytest.mark.mc
def test_the_age_name_works_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        d = data([])
        d["objects"] += [VIL, KNIGHT]
        r = replay.Replay(game, d)
        r.commands(age(0, 1, "FEUDAL_AGE"))
        for c in r.score_commands():
            out = game.command(c)
            assert "Unknown" not in out and "Incorrect" not in out and "Invalid" not in out, (c, out)
