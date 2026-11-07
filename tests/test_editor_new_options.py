"""game/editor.py: a new map gets the base terrain and the number of players that are asked for (#6078)."""
import contextlib
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import editor  # noqa: E402
from AoE2ScenarioParser.datasets.terrains import TerrainId  # noqa: E402


def test_the_new_map_has_the_terrain_and_the_players(tmp_path):
    world = str(tmp_path / "W")
    with contextlib.redirect_stdout(io.StringIO()):
        editor.new_world(world, 16, terrain="DESERT_SAND", players=4)
    with open(os.path.join(world, "aoe2mc.json")) as f:
        data = json.load(f)
    assert sum(bool(p["active"]) for k, p in data["players"].items() if k != "0") == 4     # 0: Gaia
    assert {int(v) for row in data["terrain"] for v in row.split()} == {TerrainId.DESERT_SAND.value}


def test_an_unknown_terrain_or_a_player_count_out_of_range_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="DESERT_SAN"):
        editor.new_world(str(tmp_path / "A"), 16, terrain="DESERT_SAN")
    with pytest.raises(ValueError):
        editor.new_world(str(tmp_path / "B"), 16, players=9)
    with pytest.raises(ValueError):
        editor.new_world(str(tmp_path / "C"), 16, players=0)
