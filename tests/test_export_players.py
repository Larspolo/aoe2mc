"""game/export.py: the resources and the starting age of each player (#5673)."""
import contextlib
import io
import json
import shutil

import build
import export
import savegame
from AoE2ScenarioParser.datasets.object_support import StartingAge
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def test_save_gives_the_resources_and_the_age_at_the_end(tiny_world, tmp_path):
    world = tiny_world[0]
    save = tmp_path / "save"
    shutil.copytree(world, save / "world")
    stock = {"food": 120, "wood": 340, "gold": 55, "stone": 7}
    state = {"players": {
        "1": {"soldiers": {}, "villagers": {}, "stock": stock, "techs": [build.AGE_TECHS[0]]},
        "2": {"soldiers": {}, "villagers": {}}}}
    with open(save / savegame.FILE, "w") as f:
        json.dump(state, f)
    scn = read(export.export(str(save), str(tmp_path / "end.aoe2scenario")))
    p1 = scn.player_manager.players[1]
    assert {r: getattr(p1, r) for r in stock} == stock
    assert p1.starting_age == StartingAge.FEUDAL_AGE
