"""Atonement (#1581): the monastery researches it in the Castle Age (AoE2 wiki "Atonement"), and then a monk converts
enemy monks."""
from test_monk_convert import setup, until_converted
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import monk, train

SLOT = train.ITEMS["ATONEMENT"][0]


def test_the_monastery_researches_it_only_in_the_castle_age():
    server, g = monastery(age=1)
    gold = train.price(g, "ATONEMENT")["gold"]
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["gold"] == gold
    server, g = monastery(age=2)
    rect = research(g, SLOT, gold)
    assert g.queues[rect][0]["name"] == "ATONEMENT"
    train.tick(g, train.TRAIN_TIMES["ATONEMENT"])
    assert "ATONEMENT" in g.techs


def test_only_after_it_a_monk_converts_an_enemy_monk():
    server, g = setup(("foe", "MONK", 2, 12.5))
    assert not monk.convert_order(g, {"monk"}, "foe")
    g.techs.add("ATONEMENT")
    assert monk.convert_order(g, {"monk"}, "foe")
    assert until_converted(g, "foe") <= 20 and "foe" in g.soldiers
