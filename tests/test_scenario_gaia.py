"""tools/scenarios.py gaia (#5109): the Gaia units that join a player (#5107) are in the scenario, with no animal but the
sheep."""
import contextlib
import io

import scenarios
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario


def test_the_gaia_maker_is_registered():
    assert scenarios.MAKERS["gaia"] is scenarios.gaia


def test_gaia_has_four_units_that_are_not_animals(tmp_path):
    path = scenarios.gaia(str(tmp_path / "gaia.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):                    # the parser prints much text
        scn = AoE2DEScenario.from_file(path)
    gaia = [u.unit_const for u in scn.unit_manager.units[PlayerId.GAIA]]
    animals = [c for c in gaia if c in (UnitInfo.SHEEP.ID,)]
    assert len(gaia) - len(animals) >= 4
    assert {UnitInfo.MAN_AT_ARMS.ID, UnitInfo.VILLAGER_FEMALE.ID, UnitInfo.MONK.ID,
            UnitInfo.TRADE_CART_EMPTY.ID} <= set(gaia)
