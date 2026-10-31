"""Live replay: Empire Wars, Death Match and Battle Royale replay the start state of the record and the summary names
the mode (#4897). Fake RCON."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

OBJECTS = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "x": 8.0, "y": 8.0, "ref": 11},
           {"kind": "U", "name": "VILLAGER_M", "player": 1, "x": 10.0, "y": 10.0, "ref": 12}]


def made(mode, resources=None):
    d = data([{"time": 0, "kind": "restore"}] if resources else []) | {"lobby": {"type": mode}, "objects": [dict(o) for o in OBJECTS]}
    if resources:
        d["players"]["1"] |= {"resources": resources, "saved": True}
    return replay.Replay(Fake(), d)


@pytest.mark.parametrize("mode", ["Empire Wars", "Death Match", "Battle Royale"])
def test_the_start_objects_stay_and_the_summary_names_the_mode(mode):
    r = made(mode)
    assert {o["ref"] for o in r.data["objects"]} == {11, 12} and set(r.refs) == {11, 12}
    assert any(mode in c for c in r.summary_commands()[:2])


@pytest.mark.parametrize("mode", ["Empire Wars", "Death Match", "Battle Royale"])
def test_the_stock_of_the_record_stays(mode):
    stock = {"food": 1, "wood": 2, "gold": 3, "stone": 4}
    assert made(mode, stock).resources(1) == stock


def test_death_match_starts_with_more_than_the_standard_stock():
    dm, rm = made("Death Match").resources(1), made("Empire Wars").resources(1)
    assert rm == replay.START and all(dm[k] > rm[k] for k in rm)
