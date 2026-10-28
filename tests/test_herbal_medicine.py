"""Herbal Medicine (#1585): the monastery researches it in the Castle Age (200 gold, 35 s, AoE2 DE wiki "Herbal
Medicine"), and then the units in the buildings of the player heal 6 times as fast."""
import pytest
from test_garrison_heal import CASTLE, TC, run, setup
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import civs, train


def test_the_values_are_those_of_aoe2():
    assert len(train.HELP["HERBAL_MEDICINE"]) <= 50
    assert {"BYZANTINES", "HUNS", "VIKINGS"} <= set(civs.MISSING["HERBAL_MEDICINE"])
    assert "BRITONS" not in civs.MISSING["HERBAL_MEDICINE"]


def test_the_monastery_researches_it_only_in_the_castle_age():
    slot = train.ITEMS["HERBAL_MEDICINE"][0]
    server, g = monastery(age=1)
    g.stock["gold"] = 200
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["gold"] == 200
    server, g = monastery(age=2)
    rect = research(g, slot, 200)
    assert g.queues[rect][0]["name"] == "HERBAL_MEDICINE"
    train.tick(g, 35)
    assert "HERBAL_MEDICINE" in g.techs


def test_after_it_units_in_buildings_heal_6_times_as_fast():
    server, g = setup(("a", "MILITIA", CASTLE, 10.0, 200.0), ("b", "MILITIA", TC, 10.0, 200.0))
    g.techs.add("HERBAL_MEDICINE")
    run(g, 50)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 1.2 * 50)    # 72 HP per minute
    assert server.entities["b"]["Health"] == pytest.approx(10 + 0.6 * 50)    # 36 HP per minute
