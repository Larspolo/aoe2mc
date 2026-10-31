"""A terrain layer of a DE scenario gives the look of a land tile; water keeps its base (#3688)."""
import scenarios
from AoE2ScenarioParser.datasets.terrains import TerrainId

import aoe2mc


def test_land_layer_changes_the_terrain_only_on_land(tmp_path):
    scn = scenarios.new_scenario(16)
    tiles = scn.map_manager.terrain
    for t in tiles:
        if t.x < 4 and t.y < 4:
            t.layer = TerrainId.ROAD                      # a road on grass: the look changes
        if t.x >= 12 and t.y == 0:
            t.terrain_id = TerrainId.WATER_DEEP           # a grass layer on water: the water stays
            t.layer = TerrainId.GRASS_1
        if (t.x, t.y) == (6, 6):
            t.layer = TerrainId.WATER_SHALLOW             # a water layer on grass: the grass stays
    path = str(tmp_path / "l.aoe2scenario")
    scenarios.save(scn, path)

    terrain = aoe2mc.read_scenario(path)[1]
    assert terrain[0, 0] == TerrainId.ROAD
    assert terrain[12, 0] == TerrainId.WATER_DEEP
    assert terrain[6, 6] == TerrainId.GRASS_1
    assert terrain[8, 8] == TerrainId.GRASS_1
