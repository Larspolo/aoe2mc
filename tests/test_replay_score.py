"""Live replay: a sidebar shows the population of each player (#741). Fake RCON and a fake clock."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402
from test_replay_spawn import TC, queue  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

KNIGHT = {"kind": "unit", "name": "KNIGHT", "player": 2, "uuid": "u2", "ref": 8, "tile": [12.5, 10.5]}
SHEEP = {"kind": "unit", "name": "SHEEP", "player": 1, "uuid": "u3", "ref": 11, "tile": [3.5, 3.5]}


def play(timeline, bar=True):
    d = data(timeline)
    d["objects"] += [VIL, KNIGHT, SHEEP, TC]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, bar=bar, finish=True)
    return r, [c for c in game.sent if replay.POP in c]


def sets(sent):
    return [c.split(" ", 3)[3] for c in sent if c.startswith("scoreboard players set ")]


def test_the_sidebar_starts_with_the_start_units_and_a_spawn_adds_one():
    r, sent = play([queue(t=0), dict(time=60_000, player=1, kind="chat", text="gg")])
    assert sent[:2] == ['scoreboard objectives add aoe_pop dummy "Population"',
                        "scoreboard objectives setdisplay sidebar aoe_pop"]
    assert sets(sent) == ["P1 aoe_pop 1", "P2 aoe_pop 1", "P1 aoe_pop 2"]    # the sheep does not count
    names = [c for c in sent if " display name " in c]
    assert names[0].startswith("scoreboard players display name P1 aoe_pop ")
    assert json.loads(names[0].split(" ", 6)[6]) == {"text": "Player 1 (Britons) · Dark · F 200 W 200 G 100 S 200 (est.) · APM 1 · TC idle 0:00", "color": "blue"}
    texts = {json.loads(c.split(" ", 6)[6])["text"].split(" · APM")[0] for c in names}
    assert len(texts) == 3                       # once per player, again for the cost of the villager (#932)
    assert r.pop == {1: 2, 2: 1}


def test_a_deleted_unit_takes_one_away():
    _, sent = play([delete(1000, [8], player=2), dict(time=5000, player=1, kind="chat", text="gg")])
    assert sets(sent) == ["P1 aoe_pop 1", "P2 aoe_pop 1", "P2 aoe_pop 0"]


def test_without_bar_no_score_commands():
    r, sent = play([queue(t=0), delete(1000, [8], player=2)], bar=False)
    assert sent == [] and r.pop == {1: 2, 2: 0}


@pytest.mark.mc
def test_score_commands_work_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        d = data([])
        d["objects"] += [VIL, KNIGHT]
        r = replay.Replay(game, d)
        for c in r.score_commands():
            out = game.command(c)
            assert "Unknown" not in out and "Incorrect" not in out and "Invalid" not in out, (c, out)
        assert "P1 has 1 [Population]" in game.command(f"scoreboard players get P1 {replay.POP}")
