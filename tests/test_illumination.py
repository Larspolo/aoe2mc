"""Illumination (#1583): the monastery researches it in the Imperial Age (120 gold, 65 s, AoE2 wiki "Illumination"),
and then a monk rests 33 AoE2 seconds after a conversion, not 62 (87.5 % faster; the tech tree says 50 %)."""
import pytest
from test_monk_convert import setup, until_converted
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import civs, monk, train


def test_the_values_are_those_of_aoe2():
    assert train.TECH_AGE["ILLUMINATION"] == 3 and len(train.HELP["ILLUMINATION"]) <= 50
    assert train.ITEMS["ILLUMINATION"][0] == 7 and "ILLUMINATION" in train.TRAINS["MONASTERY"]
    assert len(civs.MISSING["ILLUMINATION"]) == 14 and {"CELTS", "MAYANS", "VIKINGS"} <= set(civs.MISSING["ILLUMINATION"])
    assert "BRITONS" not in civs.MISSING["ILLUMINATION"]                 # the wiki availability chart
    assert monk.REST / monk.ILLUMINATED == pytest.approx(1.875, abs=0.01)


def test_the_monastery_researches_it_only_in_the_imperial_age():
    server, g = monastery(age=2)
    g.stock["gold"] = 120
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 7) == 0 and g.stock["gold"] == 120
    server, g = monastery(age=3)
    rect = research(g, 7, 120)
    assert g.queues[rect][0]["name"] == "ILLUMINATION"
    train.tick(g, 65)
    assert "ILLUMINATION" in g.techs


def test_after_it_the_monk_rests_33_seconds_after_a_conversion():
    server, g = setup(("a", "MILITIA", 2, 8.5), ("b", "MILITIA", 2, 9.5))
    g.techs.add("ILLUMINATION")
    monk.convert_order(g, {"monk"}, "a")
    until_converted(g, "a")
    monk.convert_order(g, {"monk"}, "b")
    assert until_converted(g, "b", limit=monk.ILLUMINATED - 1) == pytest.approx(monk.ILLUMINATED - 1)
    assert until_converted(g, "b") <= 1 + 9 * monk.INTERVAL
