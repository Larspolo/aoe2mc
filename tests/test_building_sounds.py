"""game/train.py: a click on an own building plays the sound of its line in game/data/sounds.jsonl (#3501)."""
import pytest

from game import table, train
from tools import mcvalid

from test_castle_upgrades import setup


def sounds(log):
    return [c for c in log if "playsound " in c]


def town():
    """The barracks, archery range and stable of test_castle_upgrades, a town center of player 1 and one of player 2."""
    server, g = setup()
    g.sites += [{"name": "TOWN_CENTER", "player": 1, "footprint": [2, 6, 14, 18], "done": True}]
    g.data["objects"] += [{"kind": "building", "name": "TOWN_CENTER", "player": 2, "footprint": [14, 14, 18, 18]}]
    return server, g


@pytest.mark.parametrize("cell, name", [((3, 15), "TOWN_CENTER"), ((15, 3), "STABLE")])
def test_a_click_on_an_own_building_plays_its_sound(cell, name):
    server, g = town()
    n = len(server.log)
    assert train.open_menu(g, "Steve", cell, True)
    out = sounds(server.log[n:])
    assert len(out) == 1 and f"playsound minecraft:{train.SOUNDS[name]['select']} voice @s" in out[0]
    n = len(server.log)
    train.open_menu(g, "Steve", cell, True)                            # a spam click: no second sound
    assert not sounds(server.log[n:])


def test_an_enemy_building_and_a_building_with_no_line_play_no_sound():
    server, g = town()
    n = len(server.log)
    assert train.open_menu(g, "Steve", (15, 15), True) is None         # the town center of player 2
    assert train.open_menu(g, "Steve", (3, 3), True)                   # the barracks: no line
    assert not sounds(server.log[n:])


def test_each_building_sound_is_a_building_and_a_valid_sound():
    buildings = {r["name"] for r in table.load("buildings.jsonl")}
    rows = [r for r in table.load("sounds.jsonl") if r["name"].isupper()]
    assert {r["name"] for r in rows} >= {"TOWN_CENTER", "STABLE", "BLACKSMITH"}
    assert all(r["name"] in buildings and mcvalid.sound_error(r["select"]) is None for r in rows)
