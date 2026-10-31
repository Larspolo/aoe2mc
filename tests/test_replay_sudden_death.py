"""Live replay of a Sudden Death record: a player whose town center falls is out (#4894). Fake RCON."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402
from test_replay_regicide import texts  # noqa: E402


def towns(kind):
    d = data([])
    d["lobby"] = {"type": kind, "dataset": "Definitive Edition"}
    d["objects"] = [{"kind": "building", "name": "TOWN_CENTER", "player": p, "ref": 10 + p,
                     "footprint": [16 * p - 12, 4, 16 * p - 4, 12]} for p in (1, 2)]
    return replay.Replay(Fake(), d)


def summary(r):
    return [t for t in texts(r.summary_commands()) if "town center" in t]


def test_the_fall_of_the_town_center_puts_its_player_out():
    r = towns(replay.SUDDEN_DEATH)
    assert r.towns == {1, 2}
    cmds = r.commands(delete(65000, [12], names=["TOWN_CENTER"], player=2))
    assert "Player 2 (Aztecs) is out" in texts(cmds)
    assert r.town_lost == {2: 65000}
    assert summary(r) == ["Player 2 (Aztecs): town center lost 01:05 (Sudden Death)"]
    r.pop = {1: 3, 2: 3}                                             # the panel shows the players with units
    panel = " ".join(texts(r.score_commands()))
    assert "Player 2 (Aztecs) · Out" in panel and "Player 1 (Britons) · Out" not in panel


def test_the_same_fall_in_a_random_map_game_puts_no_player_out():
    r = towns("Random Map")
    cmds = r.commands(delete(65000, [12], names=["TOWN_CENTER"], player=2))
    assert r.towns == set() and r.town_lost == {} and summary(r) == []
    assert not any("is out" in t for t in texts(cmds)) and r.town_check(90000) == []
