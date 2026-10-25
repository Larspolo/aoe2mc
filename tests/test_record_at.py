"""--at MM:SS: the state of the recorded game in samples/ at a game time (#373). Skip without `mgz`."""
import contextlib
import io
import json
import os
import re
from collections import Counter

import pytest

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")
pytest.importorskip("mgz.model")


@pytest.fixture(scope="module")
def start():
    *_, objects, players = aoe2mc.read_map(REC)
    return objects, aoe2mc.read_timeline(REC)


def test_buildings_and_units_grow_with_the_time(start):
    objects, timeline = start
    per_player = []
    for minute in (0, 10, 30):
        objs, stats = aoe2mc.apply_timeline(objects, timeline, minute * 60000)
        per_player.append(Counter(o["player"] for o in objs if o["kind"] == "B"))
        units = [o for o in objs if o["kind"] == "U" and o.get("ref") is None]
        assert len(units) == stats["units (QUEUE commands, at their building)"]
        assert all(o["name"] and not o["name"].startswith("UNKNOWN") for o in objs if o.get("ref") is None)
    assert per_player[0] == {1: 1, 2: 1}                               # the town centers
    for p in (1, 2):
        assert per_player[0][p] < per_player[1][p] < per_player[2][p]
    assert len(objects) == len(aoe2mc.apply_timeline(objects, timeline, 0)[0])      # the start state is unchanged


def test_walls_delete_and_duplicates():
    objects = [dict(kind="B", name="TOWN_CENTER", player=1, x=10.0, y=10.0, ref=5),
               dict(kind="U", name="VILLAGER_MALE", player=1, x=12.5, y=12.5, ref=6)]
    timeline = [dict(time=1, player=1, kind="wall", type=72, tile=[2.0, 3.0], end=[5, 6]),
                dict(time=2, player=1, kind="build", type=70, tile=[20.0, 20.0]),
                dict(time=3, player=1, kind="build", type=70, tile=[20.0, 20.0]),          # a second click
                dict(time=4, player=1, kind="queue", type=83, objects=[5], amount=3),
                dict(time=5, player=1, kind="delete", objects=[6]),
                dict(time=9, player=1, kind="build", type=70, tile=[30.0, 30.0])]          # after the time
    objs, stats = aoe2mc.apply_timeline(objects, timeline, 5)
    walls = [(o["x"], o["y"]) for o in objs if o["name"] == "PALISADE_WALL"]
    assert walls == [(2.5, 3.5), (3.5, 4.5), (4.5, 5.5), (5.5, 6.5)]
    assert [(o["x"], o["y"]) for o in objs if o["name"] == "HOUSE"] == [(20.0, 20.0)]
    assert [(o["name"], o["x"]) for o in objs if o["kind"] == "U"] == [("VILLAGER_MALE", 10.0)] * 3     # 6 deleted
    assert stats["start objects removed (DELETE commands)"] == 1


def test_at_option(tmp_path):
    for bad in (["--at", "12"], ["--at", "1:75"]):
        with pytest.raises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            aoe2mc.main([REC, str(tmp_path / "W"), *bad])
    assert aoe2mc.game_time("12:30") == 750000 and aoe2mc.game_time("1:02:03") == 3723000
    with pytest.raises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
        aoe2mc.main([os.path.join(ROOT, "samples", "gallery.aoe2scenario"), str(tmp_path / "W"), "--at", "1:00"])


@pytest.mark.slow
def test_record_world_at_ten_minutes(tmp_path):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.main([REC, str(tmp_path / "W"), "--at", "10:00"])
    text = out.getvalue()
    assert "state at 10:00: " in text and "units in a block (moved up): 0" in text
    assert int(re.search(r"buildings: (\d+)", text).group(1)) > 2
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        assert sum(o["kind"] == "building" for o in json.load(f)["objects"]) > 2
