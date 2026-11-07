"""game/export.py: a hero keeps its AoE2 unit ID in the export (#6034)."""
import contextlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import export  # noqa: E402
from AoE2ScenarioParser.datasets.heroes import HeroInfo  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def test_unit_id_finds_a_hero_by_its_name():
    assert export.unit_id("JOAN_OF_ARC") == HeroInfo.JOAN_OF_ARC.ID


def test_a_hero_of_the_world_exports_with_its_id_player_and_tile(tiny_world, tmp_path):
    world = tmp_path / "world"
    shutil.copytree(tiny_world[0], world)
    with open(world / "aoe2mc.json") as f:
        data = json.load(f)
    hero = {"id": export.unit_id("JOAN_OF_ARC"), "player": 1, "tile": [3, 4], "rotation": 0, "kind": "U"}
    data["objects"].append(hero)
    with open(world / "aoe2mc.json", "w") as f:
        json.dump(data, f)
    scn = read(export.export(str(world), str(tmp_path / "hero.aoe2scenario")))
    found = [u for p in scn.unit_manager.units for u in p if u.unit_const == hero["id"]]
    assert len(found) == 1
    u = found[0]
    assert int(u.player) == 1
    assert (int(u.x), int(u.y)) == (3, 4)
