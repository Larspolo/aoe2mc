"""game/gather.py: a click that selects an own unit plays one voice line of its class (#3499, game/data/sounds.jsonl)."""
import pytest

from game import gather, table
from tools import mcvalid

from test_gather import FakeServer, grid
from test_gather_attack import click


def setup():
    """Three militia, an archer and a knight near each other, and a villager (player 1)."""
    feet = {"m-1": (5.5, 64.0, 10.5), "m-2": (8.5, 64.0, 12.5), "m-3": (3.5, 64.0, 16.5), "a-1": (7.5, 64.0, 8.5),
            "k-1": (9.5, 64.0, 14.5), "v-1": (12.5, 64.0, 4.5)}
    names = {"m-1": "MILITIA", "m-2": "MILITIA", "m-3": "MILITIA", "a-1": "ARCHER", "k-1": "KNIGHT",
             "v-1": "VILLAGER_MALE"}
    objects = [{"kind": "unit", "name": n, "player": 1, "uuid": u, "tile": [0.5, 0.5]} for u, n in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    return server, gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()


def sounds(log):
    return [c for c in log if c.startswith("playsound ")]


def sound(cls):
    return f"playsound minecraft:{gather.VOICES[cls]['select']} voice "


@pytest.mark.parametrize("uuid, cls, at", [("v-1", "villager", (12.5, 4.5)), ("k-1", "cavalry", (9.5, 14.5))])
def test_a_click_on_a_unit_plays_the_voice_of_its_class(uuid, cls, at):
    server, g = setup()
    log = click(server, g, (at[0], at[1] + 3), at)
    assert g.selected == {uuid}
    assert [s.startswith(sound(cls)) for s in sounds(log)] == [True]


def test_a_box_of_five_units_plays_one_voice():
    server, g = setup()
    g.box("Steve", (2, 8))
    n = len(server.log)
    g.box("Steve", (10, 18))
    assert g.selected == {"m-1", "m-2", "m-3", "a-1", "k-1"}
    assert [s.startswith(sound("archer")) for s in sounds(server.log[n:])] == [True]   # a-1: the boss bar unit


def test_a_unit_that_leaves_the_selection_plays_no_voice():
    server, g = setup()
    g.choose({"m-1", "m-2"}, "m-1")
    n = len(server.log)
    g.choose({"m-2"}, "m-2")
    assert not sounds(server.log[n:])


def test_each_unit_class_has_a_valid_sound():
    rows = table.load("sounds.jsonl")
    assert {r["name"] for r in rows} >= {"villager", "infantry", "archer", "cavalry", "siege", "monk", "ship"}
    assert all(mcvalid.sound_error(r["select"]) is None and 0.5 <= r["pitch"] <= 2 for r in rows)
