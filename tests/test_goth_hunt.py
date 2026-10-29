"""game/civs.py LAST: the hunt of Goth players lasts longer, their herdables do not (AoE2 DE "Goths", #2375)."""
from test_civ_last import gathered


def test_goth_hunt_lasts_longer():
    assert gathered("GOTHS", carcass=(100, False)) > gathered("FRANKS", carcass=(100, False)) == 100   # a deer


def test_goth_herdables_and_other_resources_do_not_last_longer():
    assert gathered("GOTHS", carcass=(100, True)) == 100                   # a sheep is no hunt
    assert gathered("GOTHS", "GOLD_MINE") == gathered("FRANKS", "GOLD_MINE")
