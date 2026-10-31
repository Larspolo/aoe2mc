"""Live replay of a Capture the Relic record: the monk that takes the relic to its monastery wins (#4895). Fake RCON."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_regicide import texts  # noqa: E402

RECT = (20, 28, 4, 12)


def game(kind):
    d = data([])
    d["lobby"] = {"type": kind, "dataset": "Definitive Edition"}
    d["objects"] = [{"kind": "other", "name": "RELIC", "ref": 7, "tile": [8, 8]}]
    r = replay.Replay(Fake(), d)
    r.map = types.SimpleNamespace(y=lambda x, z: 70)
    r.units[30] = types.SimpleNamespace(uuid="m-30", name="MONK", player=2)
    r.pop = {1: 3, 2: 3}
    return r


def play(r):
    r.fetching[30] = 7
    r.pickup(30, r.units[30])
    panel = " ".join(texts(r.score_commands()))
    r.homing[30] = (RECT, 2)
    return panel, texts(r.deliver(30, 125000))


def summary(r):
    return [t for t in texts(r.summary_commands()) if "(Capture the Relic)" in t]


def test_the_monk_that_takes_the_relic_home_wins():
    r = game(replay.CAPTURE_RELIC)
    panel, cmds = play(r)
    assert "Player 2 (Aztecs) · Relic" in panel and "Player 1 (Britons) · Relic" not in panel
    assert any("wins" in t for t in cmds)
    assert r.relic_won == (2, 125000)
    assert summary(r) == ["Player 2 (Aztecs): wins, relic in a monastery 02:05 (Capture the Relic)"]


def test_a_random_map_record_has_no_winner_line():
    r = game("Random Map")
    panel, cmds = play(r)
    assert "· Relic" not in panel and not any("wins" in t for t in cmds)
    assert r.relic_won is None and summary(r) == []
