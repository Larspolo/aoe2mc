"""#3031: a recorded unit that walks inland is not named as a ship, for each ship type (aoe2mc.name_timeline).
The fallback gives it the last land unit of its player, also when the ship has no TRAIN line."""
import numpy as np
import pytest

import aoe2mc

WATER = np.zeros((40, 40), bool)
WATER[:, :10] = True                                     # a lake at y < 10, land from y = 10


def obj(ref, name, player=1):
    return dict(kind="B", name=name, player=player, x=0, y=0, ref=ref)


@pytest.mark.parametrize("ship", ["WAR_GALLEY", "GALLEON", "FIRE_SHIP", "DEMOLITION_SHIP", "LONGSHIP"])
def test_a_warship_inland_is_not_the_ship(ship):
    objects = [obj(5, "DOCK"), obj(6, "BARRACKS")]
    events = [dict(time=1000, player=1, kind="queue", objects=[5], name=ship, amount=1),
              dict(time=60000, player=1, kind="queue", objects=[6], name="SPEARMAN", amount=1),
              dict(time=200000, player=1, kind="move", objects=[11], tile=[20.0, 30.0])]
    assert aoe2mc.name_timeline(objects, events, water=WATER)[11] == "SPEARMAN"


def test_the_champion_is_the_inland_unit_after_a_galley():
    objects = [obj(5, "DOCK"), obj(6, "BARRACKS")]
    events = [dict(time=1000, player=1, kind="queue", objects=[6], name="CHAMPION", amount=1),
              dict(time=40000, player=1, kind="move", objects=[10], tile=[20.0, 30.0]),
              dict(time=60000, player=1, kind="queue", objects=[5], name="GALLEY", amount=1),
              dict(time=200000, player=1, kind="move", objects=[11], tile=[20.0, 30.0])]
    assert aoe2mc.name_timeline(objects, events, water=WATER)[11] == "CHAMPION"
