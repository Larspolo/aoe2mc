"""Illumination (#1583): the monastery researches it in the Imperial Age (AoE2 wiki "Illumination"), and then a monk
rests monk.ILLUMINATED AoE2 seconds after a conversion, not monk.REST."""
import pytest
from test_monk_convert import setup, until_converted
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import monk, train


def test_the_monastery_researches_it_only_in_the_imperial_age():
    slot = train.SLOTS["ILLUMINATION"]
    server, g = monastery(age=2)
    gold = train.price(g, "ILLUMINATION")["gold"]
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["gold"] == gold
    server, g = monastery(age=3)
    rect = research(g, slot, gold)
    assert g.queues[rect][0]["name"] == "ILLUMINATION"
    train.tick(g, train.seconds(g, "ILLUMINATION", "MONASTERY"))
    assert "ILLUMINATION" in g.techs


def test_after_it_the_monk_rests_a_shorter_time_after_a_conversion():
    server, g = setup(("a", "MILITIA", 2, 8.5), ("b", "MILITIA", 2, 9.5))
    g.techs.add("ILLUMINATION")
    monk.convert_order(g, {"monk"}, "a")
    until_converted(g, "a")
    monk.convert_order(g, {"monk"}, "b")
    assert until_converted(g, "b", limit=monk.ILLUMINATED - 1) == pytest.approx(monk.ILLUMINATED - 1)
    assert until_converted(g, "b") <= 1 + 9 * monk.INTERVAL
