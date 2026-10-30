"""Inquisition of the Spanish (#4326, epic #4096): the castle of the Spanish researches it; its key "convert_rate"
makes monks convert faster, and the key "unit_convert_range" gives missionaries more conversion range. The values
come from the data line (found by its key)."""
import numpy as np
from test_monk_convert import setup, until_converted
from test_train_castle import menus
from test_train_castle import setup as castle

from game import monk, train

CASTLE = (12, 4)
TECH = next(iter(train.BY_KEY["unit_convert_range"]))


def label(g, name):
    """The label of name in the castle menu of g, or None."""
    return train.layout(g, train.home(g, CASTLE)).get(name, (None, None, None))[2]


def test_only_the_castle_of_its_civ_researches_it():
    civ = train.value("civ", TECH, None)
    server, g = castle(civ, ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(g, TECH)}:" in menus(server)[-1]
    server, g = castle("BRITONS" if civ != "BRITONS" else "FRANKS", ages=2)
    assert label(g, TECH) is None


def test_a_monk_converts_faster_after_the_research():
    times = []
    for techs in ((), (TECH,)):
        server, g = setup(("foe", "MILITIA", 2, 7.5))
        g.chance = np.random.default_rng(3)
        g.techs.update(techs)
        g.converting["monk"] = ["foe", 0.0, 0]
        times.append(until_converted(g, "foe"))
    assert times[1] < times[0]


def test_a_missionary_converts_farther_after_the_research():
    unit, tiles = next(iter(train.value("unit_convert_range", TECH, {}).items()))
    reach = monk.MONKS[unit]
    server, g = setup(("far", "MILITIA", 2, 5.5 + reach + tiles))
    g.soldiers["monk"] = unit
    pos = g.positions(["monk", "far"])
    assert not monk.near(g, "monk", "far", pos)
    g.techs.add(TECH)
    assert monk.near(g, "monk", "far", pos)
