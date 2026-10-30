"""The arrows of a watch tower and a castle leave the roof in a converted world (#1249): from above the edge column of
the footprint, a steep arrow to a near enemy fell into the barrier top of that column and did no damage. The fix of
#1219 (a steep shot starts higher) is in volley(); tests/test_build_tower.py checks only a built watch tower."""
import contextlib
import io
import json
import time

import pytest

from game import combat, run


@pytest.mark.mc
def test_tower_and_castle_hit_a_near_enemy(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(48)
    um = scn.unit_manager
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.WATCH_TOWER.ID, x=38, y=10)
    um.add_unit(scenarios.PlayerId.ONE, BuildingInfo.CASTLE.ID, x=10, y=38)
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=38.5, y=15.5)     # 4 tiles south of the tower
    um.add_unit(scenarios.PlayerId.TWO, UnitInfo.MILITIA.ID, x=10.5, y=31.5)     # 4 tiles north of the castle
    src = str(tmp_path / "a.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    enemies = {round(o["tile"][1]): o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["player"] == 2}
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        for u in enemies.values():             # many hit points, the pierce armor of a militia (1), no AI: it stands
            game.command(f"aoe stats {u} 1000 4 0 1 0 infantry - 40")
            game.command(f"data merge entity {u} {{NoAI:1b}}")
        time.sleep(6)
        hp = {t: float(game.command(f"data get entity {u} Health").rsplit(" ", 1)[-1].rstrip("f"))
              for t, u in enemies.items()}
    tower, castle = (combat.stats(n).attack - 1 for n in ("WATCH_TOWER", "CASTLE"))   # an arrow: attack - pierce armor 1
    assert hp[16] <= 1000 - tower and hp[32] <= 1000 - castle, hp
