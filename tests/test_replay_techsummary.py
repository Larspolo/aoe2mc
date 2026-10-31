"""Live replay: the age-up times and the research count of each player in the summary at the end (#1067)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import lang  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TIMELINE = [{"time": 1000, "player": 1, "kind": "research", "objects": [], "technology": "Loom"},
            {"time": 620_620, "player": 1, "kind": "age", "age": "FEUDAL_AGE"},
            {"time": 700_000, "player": 2, "kind": "research", "objects": [], "technology": "Wheelbarrow"},
            {"time": 1_265_000, "player": 1, "kind": "age", "age": "CASTLE_AGE"},
            {"time": 1_300_000, "player": 1, "kind": "research", "objects": [], "technology": "Forging"},
            {"time": 1_400_000, "player": 1, "kind": "chat", "text": "gg"}]


def play(**kw):
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, data(TIMELINE))
    r.run(speed=8, clock=lambda: now[0], sleep=sleep, log=None, bar=True, **kw)
    return r, game.sent


def lines(sent):
    return ["".join(lang.plain(t) for t in json.loads(c.split(" ", 2)[2])) for c in sent
            if c.startswith("tellraw @a [") and "technologies" in c]


WANT = ["Player 1 (Britons): Feudal 10:20, Castle 21:05, Imperial -, technologies 2",
        "Player 2 (Aztecs): Feudal -, Castle -, Imperial -, technologies 1"]


def test_the_summary_shows_the_age_up_times_and_the_research_count():
    r, sent = play()
    assert r.reached[1] == {"FEUDAL_AGE": 620_620, "CASTLE_AGE": 1_265_000} and r.researched == {1: 2, 2: 1}
    assert lines(sent) == WANT


def test_a_jump_over_the_age_ups_keeps_the_times_and_the_count():
    r, sent = play(to=1_350_000)
    assert lines(sent) == WANT


def test_mmss():
    assert replay.mmss(0) == "00:00" and replay.mmss(620_620) == "10:20" and replay.mmss(3_725_000) == "62:05"
