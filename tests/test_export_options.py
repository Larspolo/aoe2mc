"""game/export.py: the export keeps the Options tab, the map settings and the cinematics of the source (#6052)."""
import contextlib
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import export  # noqa: E402
import scenarios  # noqa: E402
from AoE2ScenarioParser.datasets.trigger_lists import ColorMood  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def values(scn):
    pl = scn.player_manager.players[1]
    return (list(pl.disabled_techs), list(pl.disabled_units), list(pl.disabled_buildings),
            scn.option_manager.lock_teams, scn.map_manager.map_color_mood, scn.sections["Cinematics"].ascii_pregame,
            scn.sections["Map"].script_name)


def test_the_export_keeps_the_options_mood_and_cinematics(tmp_path):
    with tempfile.TemporaryDirectory() as tmp:
        scn = read(scenarios.tiny(os.path.join(tmp, "tiny.aoe2scenario")))
    pl = scn.player_manager.players[1]
    pl.disabled_techs, pl.disabled_units, pl.disabled_buildings = [22, 101], [4], [12]
    scn.option_manager.lock_teams = True
    scn.map_manager.map_color_mood = ColorMood.AUTUMN
    scn.sections["Cinematics"].ascii_pregame = "intro.mp4"
    scn.sections["Map"].script_name = "Arabia"
    src = scenarios.save(scn, str(tmp_path / "src.aoe2scenario"))
    want = values(read(src))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
        out = export.export(str(tmp_path / "W"), str(tmp_path / "out.aoe2scenario"))
    assert values(read(out)) == want and want[3] is True

    with open(os.path.join(tmp_path, "W", "aoe2mc.json")) as f:
        data = json.load(f)
    os.remove(os.path.join(tmp_path, "W", data["source"]))            # no source: the defaults, as before
    with contextlib.redirect_stdout(io.StringIO()):
        out = export.export(str(tmp_path / "W"), str(tmp_path / "plain.aoe2scenario"))
    assert values(read(out))[:4] == ([], [], [], False)
