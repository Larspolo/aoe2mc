"""Live replay: a title, the end time and a sound show that the replay is over (#872). Fake RCON and a fake clock."""
import json
import os
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def play(timeline, **kw):
    now = [0.0]

    def sleep(s):
        now[0] += s
    game = Fake()
    replay.Replay(game, data(timeline)).run(speed=4, clock=lambda: now[0], sleep=sleep, log=None, **kw)
    return game.sent


def test_the_end_shows_a_title_the_end_time_and_one_sound():
    sent = play([{"time": 0, "player": 1, "kind": "chat", "text": "hi"},
                 {"time": 2_662_500, "player": 1, "kind": "resign"}], bar=True)
    titles = [c for c in sent if c.startswith("title @a")]
    assert titles[-3:] == ["title @a times 10 100 20", "title @a subtitle " + json.dumps(replay.say("game_time", "44:22")),
                           "title @a title " + json.dumps(replay.say("replay_ended"))]
    assert sent.index("title @a title " + json.dumps(replay.say("replay_ended"))) > max(i for i, c in enumerate(sent) if "resigns" in c)
    assert [c for c in sent if c.startswith("playsound")] == [
        "playsound minecraft:ui.toast.challenge_complete master @a ~ ~ ~ 1 1 1"]
    names = [c.split(" name ")[1] for c in sent if c.startswith("bossbar") and " name " in c]
    assert names[-1] == '{"text": "End 44:22"}'                        # the boss bar keeps the end time


def test_without_bar_no_end_title():
    assert not [c for c in play([{"time": 0, "player": 1, "kind": "chat", "text": "hi"}]) if "Replay ended" in c]


@pytest.mark.mc
def test_end_commands_parse_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        outs = [game.command(c) for c in replay.Replay.end_commands(65_000)]
    assert not [o for o in outs if "Unknown" in o or "Incorrect" in o or "Invalid" in o or "<--[HERE]" in o], outs
