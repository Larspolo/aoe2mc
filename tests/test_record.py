"""Convert the start state of the recorded game in samples/ (#139). Skip without `mgz`."""
import json
import os
import subprocess
import sys
from collections import Counter

import pytest
import world_reader

import aoe2mc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REC = os.path.join(ROOT, "samples", "de-64.3.aoe2record")
model = pytest.importorskip("mgz.model")


@pytest.fixture(scope="module")
def match():
    with open(REC, "rb") as f:
        return model.parse_match(f)


def test_read_record_matches_header(match):
    size, terrain, elevation, _, texts, objects, players = aoe2mc.read_map(REC)
    assert size == match.map.dimension == 120 and terrain.shape == elevation.shape == (120, 120)
    assert elevation.max() == max(t.elevation for t in match.map.tiles)
    assert players[1]["civ"] == "BYZANTINES" and players[1]["arch"] == "mediterranean" and players[1]["color"] == "red"
    assert players[2]["arch"] == "mesoamerican" and players[2]["color"] == "orange"
    assert players[1]["view"] == (37.0, 98.0) and not any(texts[k] for k in aoe2mc.CHAPTERS)
    for p in match.players:
        names = Counter(o["name"] for o in objects if o["player"] == p.number)
        assert names["TOWN_CENTER"] == sum(o.object_id == 109 for o in p.objects) == 1     # no annex parts
        villagers = names["VILLAGER_MALE"] + names["VILLAGER_FEMALE"]
        assert villagers == sum(o.name == "Villager" for o in p.objects) == 3
    assert sum(o["player"] == 0 for o in objects) == len(match.gaia)


@pytest.mark.slow
def test_record_world_positions(tmp_path):
    out = subprocess.run([sys.executable, os.path.join(ROOT, "aoe2mc.py"), REC, str(tmp_path / "w")],
                         capture_output=True, text=True, check=True).stdout
    assert "units in a block (moved up): 0" in out
    w = world_reader.World(str(tmp_path / "w"))
    tc = [w.block(148, y, 392) for y in range(80, 100)]          # town center of player 1 at tile (37, 98)
    assert "minecraft:smooth_sandstone" in tc                    # mediterranean walls
    scout = [e for e in w.entities() if e["id"] == "minecraft:horse"
             and [float(v) for v in e["Pos"]][::2] == [130.0, 422.0]]   # scout cavalry at tile (32.5, 105.5)
    assert scout
    with open(tmp_path / "w" / "aoe2mc.json") as f:
        timeline = json.load(f)["timeline"]
    assert len(timeline) == 3063 and timeline[0]["time"] == 0


def test_timeline_of_the_sample_record():
    timeline = aoe2mc.read_timeline(REC)
    kinds = Counter(e["kind"] for e in timeline)
    assert {k: kinds[k] for k in ("build", "wall", "queue", "research", "move", "order", "delete", "resign", "chat",
                                  "age")} == dict(build=211, wall=13, queue=469, research=44, move=1436, order=406,
                                                  delete=10, resign=1, chat=7, age=5)
    assert [e["time"] for e in timeline] == sorted(e["time"] for e in timeline)
    build = next(e for e in timeline if e["kind"] == "build")
    assert build == dict(time=3133, player=2, kind="build", type=70, name="HOUSE", tile=[85.0, 27.0], objects=[1663, 1662])
    queue = next(e for e in timeline if e["kind"] == "queue")      # mgz itself gives ERROR for these (de_queue)
    assert (queue["name"], queue["amount"], queue["objects"]) == ("VILLAGER_MALE", 1, [1652])
    wall = next(e for e in timeline if e["kind"] == "wall")
    assert (wall["name"], wall["tile"], wall["end"]) == ("PALISADE_WALL", [64.0, 54.0], [64, 54])
    tech = next(e for e in timeline if e["kind"] == "research")
    assert (tech["time"], tech["technology"], tech["technology_id"]) == (394563, "Loom", 22)
    chat = [e for e in timeline if e["kind"] == "chat"]
    assert chat[0]["player"] == 1 and chat[0]["text"].startswith("Rocky Forest or Acrop?")
    assert next(e for e in timeline if e["kind"] == "age") == dict(time=620620, player=2, kind="age", age="FEUDAL_AGE")
