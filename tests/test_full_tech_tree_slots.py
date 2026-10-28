"""Full Tech Tree gives each shown item of a menu its own slot (#3098): a regional item that has the slot of a
generic item (the Armored Elephant, the Battering Ram) takes a free slot, and a click queues the shown item."""
import pytest
from test_full_tech_tree import game

from game import build, train

civs = train.civs
SIEGE = (20, 23, 2, 5)


def homes(g):
    g.techs.update(build.AGE_TECHS)
    g.sites += [{"name": n, "player": 1, "footprint": [x, x + 3, 2, 5], "done": True} for n, x in
                (("SIEGE_WORKSHOP", 20), ("DOCK", 26), ("CASTLE", 32), ("MONASTERY", 38), ("BLACKSMITH", 44))]
    return train.homes(g)


@pytest.mark.parametrize("full", (False, True))
def test_each_shown_item_has_its_own_slot(full):
    for civ in sorted({r["name"] for r in civs.ROWS}):
        _, g = game(civ, full)
        for rect, building in homes(g).items():
            slots = [s for s, *_ in train.layout(g, rect).values()]
            assert len(slots) == len(set(slots)), (civ, building)


def test_the_britons_get_the_ram_and_the_armored_elephant():
    _, g = game("BRITONS")
    homes(g)
    shown = train.layout(g, SIEGE)
    assert shown["BATTERING_RAM"][0] == 0 and shown["ARMORED_ELEPHANT"][0] >= train.MORE
    for name in ("BATTERING_RAM", "ARMORED_ELEPHANT"):
        g.queues.clear()
        assert train.order(g, "Steve", SIEGE, train.layout(g, SIEGE)[name][0]) == 1
        assert g.queues[SIEGE][0]["name"] == name


def test_the_bengalis_keep_the_armored_elephant_in_slot_0():
    _, g = game("BENGALIS", full=False)
    homes(g)
    assert train.layout(g, SIEGE)["ARMORED_ELEPHANT"][0] == 0
