"""game/export.py: the disabled objects and the color mood of aoe2mc.json reach the scenario (#6084)."""
import contextlib
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.buildings import BuildingInfo  # noqa: E402
from AoE2ScenarioParser.datasets.techs import TechInfo  # noqa: E402
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood  # noqa: E402
from AoE2ScenarioParser.datasets.units import UnitInfo  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def world(tmp_path, src_setup=None):
    """A converted world of the tiny map; src_setup edits the source scenario before the conversion."""
    scn = read(scenarios.tiny(str(tmp_path / "tiny.aoe2scenario")))
    if src_setup:
        src_setup(scn)
    src = scenarios.save(scn, str(tmp_path / "src.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    return tmp_path / "W"


def edit(w, change):
    """Change aoe2mc.json of the world w, then drop its source: only the editor's values remain."""
    path = w / "aoe2mc.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))
    os.remove(w / data["source"])


def export_of(w, tmp_path, name):
    out = tmp_path / name
    with contextlib.redirect_stdout(io.StringIO()):
        export.export(str(w), str(out))
    return read(out)


def test_the_export_writes_the_disabled_objects_and_the_mood_of_the_json(tmp_path):
    w = world(tmp_path)
    tech = aoe2mc.tech_names()[TechInfo.ANARCHY.ID]               # the name of the json file

    def change(data):
        data["players"]["1"]["disabled"] = [tech, "MONASTERY", "MILITIA"]
        data["mood"] = "AUTUMN"

    edit(w, change)
    scn = export_of(w, tmp_path, "out.aoe2scenario")
    pl = scn.player_manager.players[1]
    assert list(pl.disabled_techs) == [TechInfo.ANARCHY.ID]
    assert list(pl.disabled_buildings) == [BuildingInfo.MONASTERY.ID]
    assert list(pl.disabled_units) == [UnitInfo.MILITIA.ID]
    assert scn.map_manager.map_color_mood == ColorMood.AUTUMN


def test_the_json_wins_over_the_source_scenario(tmp_path):
    def src_setup(scn):
        pl = scn.player_manager.players[1]
        pl.disabled_techs, pl.disabled_units = [TechInfo.ANARCHY.ID], [UnitInfo.MILITIA.ID]
        scn.map_manager.map_color_mood = ColorMood.AUTUMN

    w = world(tmp_path, src_setup)
    arbalester = aoe2mc.tech_names()[TechInfo.ARBALESTER.ID]

    def change(data):
        data["players"]["1"]["disabled"] = [arbalester]
        data["mood"] = "WINTER"

    edit(w, change)
    scn = export_of(w, tmp_path, "out.aoe2scenario")
    pl = scn.player_manager.players[1]
    assert list(pl.disabled_techs) == [TechInfo.ARBALESTER.ID]
    assert list(pl.disabled_units) == []
    assert scn.map_manager.map_color_mood == ColorMood.WINTER


def test_an_unknown_name_gives_one_line_and_no_error(tmp_path):
    w = world(tmp_path)

    def change(data):
        data["players"]["1"]["disabled"] = ["NOT_A_THING"]

    edit(w, change)
    with contextlib.redirect_stdout(io.StringIO()) as buf:
        export.export(str(w), str(tmp_path / "out.aoe2scenario"))
    lines = [line for line in buf.getvalue().splitlines() if "NOT_A_THING" in line]
    assert len(lines) == 1
    assert read(tmp_path / "out.aoe2scenario").player_manager.players[1].disabled_units == []
