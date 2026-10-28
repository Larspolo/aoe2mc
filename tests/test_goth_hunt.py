"""game/civs.py LAST: the hunt of Goth players lasts 20 % longer, their herdables do not (AoE2 DE "Goths": "Hunters
carry food +15; hunt lasts 20% longer", #2375)."""
from test_civ_last import gathered


def test_goth_hunt_lasts_20_percent_longer():
    assert gathered("GOTHS", carcass=(100, False)) == 120                  # a deer: 1 / 1.2 of a unit at each step
    assert gathered("FRANKS", carcass=(100, False)) == 100


def test_goth_herdables_and_other_resources_do_not_last_longer():
    assert gathered("GOTHS", carcass=(100, True)) == 100                   # a sheep is no hunt
    assert gathered("GOTHS", "GOLD_MINE") == 800
