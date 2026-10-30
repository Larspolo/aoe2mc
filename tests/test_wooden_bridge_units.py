"""Units on a wooden bridge stay on the deck, like on the stone bridge (#465)."""
import contextlib
import io

import scenarios
import world_reader
from AoE2ScenarioParser.datasets.buildings import BuildingInfo
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.terrains import TerrainId
from AoE2ScenarioParser.datasets.units import UnitInfo

import aoe2mc


def test_villagers_stand_on_the_wooden_bridge(tmp_path):
    scn = scenarios.new_scenario(16)
    for t in scn.map_manager.terrain:
        if 6 <= t.y <= 9:
            t.terrain_id = TerrainId.WATER_DEEP
    um = scn.unit_manager
    for y in range(5, 11):
        um.add_unit(PlayerId.GAIA, BuildingInfo.WOODEN_BRIDGE_A_MIDDLE.ID, x=8.5, y=y + 0.5)
    for x, y in ((8.5, 6.5), (8.5, 7.5), (8.5, 8.5), (8.5, 9.5), (8.02, 7.5), (8.98, 8.5)):   # 2 at the edge posts
        um.add_unit(PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=x, y=y)
    src = scenarios.save(scn, str(tmp_path / "bridge.aoe2scenario"))
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        aoe2mc.convert(src, str(tmp_path / "World"))
    log = out.getvalue()
    assert "units in a block (moved up): 0" in log, log
    assert "units moved out of a building or obstacle" not in log or "obstacle: 0" in log, log
    w = world_reader.World(str(tmp_path / "World"))
    vills = [e for e in w.entities() if str(e["id"]) == "minecraft:villager"]
    assert len(vills) == 6
    T = 4
    for e in vills:
        x, y, z = (float(v) for v in e["Pos"])
        assert 8 * T <= x < 9 * T and 6 * T <= z < 10 * T, (x, z)              # still on the bridge tiles
        below = w.block(int(x // 1), int(y) - 1, int(z // 1))
        assert below.split("[")[0].endswith(("_planks", "_slab", "_log", "_fence")), below   # not in the water
        for k in (0, 1):                                                       # not inside a post or a rail
            assert w.block(int(x // 1), int(y) + k, int(z // 1)).split("[")[0] in ("air", "minecraft:air"), (x, y, z)
