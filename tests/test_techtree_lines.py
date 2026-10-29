"""#3533: the tech tree puts the items of one unit line in one column, as the lines of the AoE2 DE tree."""
from game import techtree, train


def column(slots, name):
    return next(s for s, n in slots.items() if n == name) % techtree.WIDTH, next(s for s, n in slots.items() if n == name) // techtree.WIDTH


def test_the_militia_line_has_one_column():
    slots = techtree.pages(train.TRAINS["BARRACKS"])[0]
    assert [column(slots, n) for n in ("MILITIA", "MAN_AT_ARMS_UPGRADE", "LONG_SWORDSMAN_UPGRADE")] \
        == [(column(slots, "MILITIA")[0], techtree.age(n)) for n in ("MILITIA", "MAN_AT_ARMS_UPGRADE", "LONG_SWORDSMAN_UPGRADE")]


def test_the_spearman_line_has_another_column():
    slots = techtree.pages(train.TRAINS["BARRACKS"])[0]
    assert column(slots, "SPEARMAN")[0] == column(slots, "PIKEMAN_UPGRADE")[0] != column(slots, "MILITIA")[0]


def test_each_item_of_each_building_has_a_slot():
    for names in train.TRAINS.values():
        ps = techtree.pages(names)
        assert sorted(n for p in ps for n in p.values()) == sorted(names)
