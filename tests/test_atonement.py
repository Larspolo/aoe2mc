"""Atonement (#1581): the monastery researches it in the Castle Age (325 gold, 40 s, AoE2 wiki "Atonement"), and then
a monk converts enemy monks."""
from test_monk_convert import setup, until_converted
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import civs, monk, train


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["ATONEMENT"]) <= 50
    assert {"BRITONS", "CELTS", "WEI"} <= set(civs.MISSING["ATONEMENT"])
    assert "AZTECS" not in civs.MISSING["ATONEMENT"]


def test_the_monastery_researches_it_only_in_the_castle_age():
    server, g = monastery(age=1)
    g.stock["gold"] = 325
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 5) == 0 and g.stock["gold"] == 325
    server, g = monastery(age=2)
    rect = research(g, 5, 325)
    assert g.queues[rect][0]["name"] == "ATONEMENT"
    train.tick(g, 40)
    assert "ATONEMENT" in g.techs


def test_only_after_it_a_monk_converts_an_enemy_monk():
    server, g = setup(("foe", "MONK", 2, 12.5))
    assert not monk.convert_order(g, {"monk"}, "foe")
    g.techs.add("ATONEMENT")
    assert monk.convert_order(g, {"monk"}, "foe")
    assert until_converted(g, "foe") <= 20 and "foe" in g.soldiers
