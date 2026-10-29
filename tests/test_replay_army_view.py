"""Live replay: the army of each player in the sky, below the graphs (#3696). Fake RCON."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 5, "tile": [8.0, 8.0], "footprint": [26, 26, 38, 38]}


def make(timeline=()):
    d = data(list(timeline))
    d["objects"].append(TC)
    return replay.Replay(Fake(), d)


def shown(cmd):
    """The text component of an army command (a summon or a data merge)."""
    return json.loads(re.search(r"text:(\{[^}]*\})", cmd)[1])


def test_the_first_call_summons_one_text_per_player_and_a_second_call_sends_nothing():
    r = make()
    r.troop(1, "KNIGHT")
    r.troop(1, "KNIGHT")
    r.troop(1, "ARCHER")
    first = r.army_view(0)
    assert len(first) == 2 and all(c.startswith("summon text_display") for c in first)   # one per player
    assert f'"{replay.ARMY}.1"' in first[0] and f'"{replay.ARMY}.2"' in first[1]
    assert shown(first[0]) == {"text": "Player 1 (Britons): 2 Knight, 1 Archer", "color": r.label(1)[1]}
    assert shown(first[1]) == {"text": "Player 2 (Aztecs): -", "color": r.label(2)[1]}
    assert r.army_view(0) == []                                      # the same counts: no command


def test_a_change_of_the_army_sends_one_data_merge():
    r = make()
    r.troop(1, "KNIGHT")
    r.army_view(0)
    r.troop(1, "KNIGHT")
    (merge,) = r.army_view(1000)
    assert merge.startswith("data merge entity @e[type=text_display,tag=aoe2mc.army.1,limit=1] ")
    assert shown(merge)["text"] == "Player 1 (Britons): 2 Knight"


def test_a_unit_in_training_and_the_losses_show_until_the_training_ends():
    r = make([{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "KNIGHT"}])
    r.fallen[1] = {"ARCHER": 3, "KNIGHT": 2}
    summon = r.army_view(500)[0]
    assert shown(summon)["text"] == "Player 1 (Britons): - · training 1 Knight · lost 5"
    end = r.trainings[0][0]
    (merge,) = r.army_view(end)                                      # the unit is out: the training goes
    assert shown(merge)["text"] == "Player 1 (Britons): - · lost 5"
