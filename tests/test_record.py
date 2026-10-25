"""Convert the start state of the recorded game in samples/ (#139). Skip without `mgz`."""
import os
import subprocess
import sys
from collections import Counter

import pytest

import aoe2mc
import world_reader

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
    assert players[1]["view"] == (37.0, 98.0) and not any(texts.values())
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
