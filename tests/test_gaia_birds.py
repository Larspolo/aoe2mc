"""A Gaia bird stays Gaia: it does not join the first player whose unit comes near it (#5698, part of #5448)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gaia  # noqa: E402

import units  # noqa: E402


def gaia_unit(name):
    return {"kind": "unit", "player": 0, "uuid": "00000000-0000-0000-0000-0000000000b1", "name": name}


def test_gaia_bird_does_not_join():
    assert units.is_bird("HAWK")
    assert gaia.joinable(gaia_unit("HAWK")) is False


def test_gaia_villager_still_joins():
    assert not units.is_bird("MILITIA")
    assert gaia.joinable(gaia_unit("MILITIA")) is True
