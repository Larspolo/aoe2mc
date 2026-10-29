"""units.py: the Viking unique ship LONGBOAT (the AoE2 DE name, LONGSHIP before) is a boat with the crew of the
LONGSHIP, as the other ships (#1257). So a monk does not heal it (monk.healable uses units.is_boat)."""
import pytest

import units


@pytest.mark.parametrize("name", ["LONGBOAT", "ELITE_LONGBOAT"])
def test_the_longboat_is_a_boat_with_the_longship_crew(name):
    d = units.classify(name)
    assert units.is_boat(d)
    assert [str(p["id"]) for p in d["Passengers"]] == [str(p["id"]) for p in units.classify("LONGSHIP")["Passengers"]]
