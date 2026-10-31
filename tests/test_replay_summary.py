"""Live replay: a chat summary of the economy of each player at the end (#1065). Fake RCON and a fake clock."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import gather  # noqa: E402
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_gather import TREE, VIL, order  # noqa: E402
from test_replay_score import KNIGHT, TC  # noqa: E402
from test_replay_spawn import queue  # noqa: E402

HEAD = "tellraw @a " + json.dumps(replay.say("summary", bold=True))


def play(timeline, **kw):
    d = data(timeline)
    d["objects"] += [VIL, KNIGHT, TC, TREE]
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.run(clock=lambda: now[0], sleep=sleep, log=None, bar=True, **kw)
    return r, game.sent


def summary(sent):
    """The player lines after the summary header."""
    rest = sent[sent.index(HEAD) + 1:]
    return ["".join(lang.plain(t) for t in json.loads(c.split(" ", 2)[2])) for c in rest if c.startswith("tellraw @a [") and "villagers" in c]


def test_the_end_shows_the_villagers_and_the_gathered_resources():
    r, sent = play([queue(t=0), queue(t=1000, name="ARCHER", type=4), order(2000, 20),
                    dict(time=60_000, player=1, kind="chat", text="gg")])
    wood = gather.TREE_WOOD - r.map.trees[(5, 10)]
    assert wood > 10 and r.villagers == {1: 1}
    assert summary(sent) == [f"Player 1 (Britons): villagers trained 1, gathered food 0, wood {wood}, gold 0, stone 0, idle villager time 0:02, idle TC time 0:00",
                             "Player 2 (Aztecs): villagers trained 0, gathered food 0, wood 0, gold 0, stone 0, idle villager time 0:00, idle TC time 0:00"]
    assert sent.index(HEAD) > sent.index("title @a title " + json.dumps(replay.say("replay_ended")))


def test_a_jump_to_the_end_counts_the_same_villagers():
    timeline = [queue(t=0), queue(t=30_000), dict(time=90_000, player=1, kind="chat", text="gg")]
    r, sent = play(timeline, to=90_000)
    assert r.villagers == {1: 2} and summary(sent)[0].startswith("Player 1 (Britons): villagers trained 2,")


def test_without_bar_no_summary():
    d = data([queue(t=0)])
    game = Fake()
    replay.Replay(game, d).run(clock=lambda: 0.0, sleep=lambda s: None, log=None, finish=True)
    assert not [c for c in game.sent if "Summary" in c]


@pytest.mark.mc
def test_summary_commands_parse_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    r = replay.Replay(Fake(), data([]))
    r.villagers, r.gathered = {1: 3}, {1: {"food": 5, "wood": 7, "gold": 0, "stone": 0}}
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        outs = [game.command(c) for c in r.summary_commands()]
    assert not [o for o in outs if "Unknown" in o or "Incorrect" in o or "Invalid" in o or "<--[HERE]" in o], outs
