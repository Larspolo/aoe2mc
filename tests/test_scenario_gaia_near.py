"""tools/scenarios.py gaia (#5111): the Gaia Man-at-Arms and villager stand within gaia.RANGE tiles of a unit of player 1,
so they join it at the start; the monk and the trade cart stand farther, so they wait for the scout."""
import contextlib
import io
import math

import gaia
import scenarios
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario


def test_the_start_units_are_near_player_1_and_the_far_units_are_not(tmp_path):
    path = scenarios.gaia(str(tmp_path / "gaia.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):                    # the parser prints much text
        scn = AoE2DEScenario.from_file(path)
    um = scn.unit_manager.units
    mine = [(u.x, u.y) for u in um[PlayerId.ONE] if u.unit_const != 109]   # 109: the town center
    near = lambda u: min(math.dist((u.x, u.y), p) for p in mine) <= gaia.RANGE   # noqa: E731
    by = {u.unit_const: u for u in um[PlayerId.GAIA]}
    assert near(by[UnitInfo.MAN_AT_ARMS.ID]) and near(by[UnitInfo.VILLAGER_FEMALE.ID])
    assert not near(by[UnitInfo.MONK.ID]) and not near(by[UnitInfo.TRADE_CART_EMPTY.ID])
