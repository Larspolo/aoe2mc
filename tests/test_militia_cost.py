"""game/train.py: the militia and the man-at-arms cost 50 food and 20 gold (AoE2 DE wiki infobox, since update 141935;
#1417)."""
from game import train


def test_the_militia_and_the_man_at_arms_cost_the_aoe2_de_values():
    assert train.COSTS["MILITIA"] == {"food": 50, "gold": 20}
    assert train.COSTS["MAN_AT_ARMS"] == {"food": 50, "gold": 20}
