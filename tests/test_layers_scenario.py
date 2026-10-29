"""The test scenario `layers` of tools/scenarios.py (#3690): terrain layers on grass and on water."""
import contextlib
import io

from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc


def test_layers_scenario(tmp_path):
    import scenarios
    path = scenarios.layers(str(tmp_path / "layers.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(path)
    assert sum(t.layer != -1 for t in scn.map_manager.terrain) > 50
    size, terrain, *_ = aoe2mc.read_scenario(path)
    assert size == 32
    assert terrain[15, 2] == TerrainId.ROAD and terrain[2, 15] == TerrainId.ROAD
    assert terrain[30, 10] == TerrainId.WATER_DEEP          # a land layer on water: the water stays
