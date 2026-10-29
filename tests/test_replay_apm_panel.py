"""Live replay: the actions per minute of each player in the score panel (#3764)."""
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


def names(cmds):
    return [json.loads(c.split(" ", 6)[6])["text"] for c in cmds if " display name P1 " in c]


def test_the_display_name_ends_with_the_actions_of_the_last_minute():
    r = game(act(10_000), act(50_000), act(70_000))
    r.pop, r.ages = {1: 1}, {1: "Dark"}
    assert names(r.score_commands(60_000)) == ["Player 1 (Britons) · Dark · F 200 W 200 G 100 S 200 (est.) · APM 2 · TC idle 0:00"]


def test_a_second_call_at_the_same_time_sends_no_name():
    r = game(act(10_000), act(50_000))
    r.pop, r.ages = {1: 1}, {1: "Dark"}
    r.score_commands(60_000)
    assert names(r.score_commands(60_000)) == []


def test_the_name_without_a_time_has_no_apm_part():
    r = game(act(50_000))
    r.pop, r.ages = {1: 1}, {1: "Dark"}
    assert names(r.score_commands()) == ["Player 1 (Britons) · Dark · F 200 W 200 G 100 S 200 (est.)"]
