"""Live replay: the actions per minute of each player (#3763): the last minute, and the average in the summary."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402


def game(*events):
    return replay.Replay(Fake(), data(list(events)))


def act(t, p=1):
    return dict(time=t, player=p, kind="move")


def test_the_last_minute_counts_the_actions_of_the_player():
    r = game(act(10_000), act(50_000), act(70_000), dict(time=55_000, player=1, kind="chat", text="gg"))
    assert r.apm(1, 60000) == 2 and r.apm(1, 70000) == 2 and r.apm(2, 60000) == 0


def test_the_average_counts_all_actions_up_to_the_time():
    r = game(act(10_000), act(50_000), act(70_000), dict(time=55_000, player=1, kind="chat", text="gg"))
    assert r.mean_apm(1, 60000) == 2 and r.mean_apm(1, 0) == 0


def test_the_summary_line_ends_with_the_average_apm():
    r = game(act(10_000), act(50_000), act(70_000))
    r.ended, r.army = 60000, {1: 0}                 # the summary lists the players of the military counts
    lines = [json.loads(c.split(" ", 2)[2]) for c in r.summary_commands() if "military units trained" in c]
    assert ["".join(t["text"] for t in line) for line in lines][0].endswith("buildings lost 0, APM 2")
