"""Unique technology of the Aztecs (#2041): the castle of the Aztecs researches Atlatl in the Castle Age. Skirmishers
get more attack and range.
Only the Aztecs have it (the key "civ" of data/train.jsonl)."""
from menu_line import item
from test_train_castle import menus, setup

from game import train

CASTLE = (12, 4)


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_only_the_castle_of_the_aztecs_researches_it():
    server, g = setup("AZTECS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert item(menus(server)[-1], "Atlatl").endswith(":Atlatl:" + text(g, "ATLATL") + "research")
    server, g = setup("BRITONS", ages=2)
    train.open_menu(g, "Steve", CASTLE)
    assert "Atlatl" not in menus(server)[-1]


def test_the_effect_gives_the_skirmishers_more_attack_and_range():
    server, g = setup("AZTECS", food=2000, wood=0, gold=2000, ages=2)
    before, arb = train.stats(g, "SKIRMISHER"), train.stats(g, "ARBALESTER")
    assert train.queue(g, "Steve", CASTLE, "ATLATL")
    train.tick(g, train.TRAIN_TIMES["ATLATL"])
    assert "ATLATL" in g.techs
    after = train.stats(g, "SKIRMISHER")
    assert after.attack > before.attack and after.range > before.range
    assert train.stats(g, "ARBALESTER") == arb                                 # not skirmishers: no change
