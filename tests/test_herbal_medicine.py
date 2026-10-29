"""Herbal Medicine (#1585): the monastery researches it in the Castle Age (AoE2 DE wiki "Herbal Medicine"), and then the
units in the buildings of the player heal 6 times as fast."""
import pytest
from test_garrison_heal import CASTLE, TC, run, setup
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import train


def test_the_monastery_researches_it_only_in_the_castle_age():
    slot = train.ITEMS["HERBAL_MEDICINE"][0]
    server, g = monastery(age=1)
    gold = train.price(g, "HERBAL_MEDICINE")["gold"]
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock["gold"] == gold
    server, g = monastery(age=2)
    rect = research(g, slot, gold)
    assert g.queues[rect][0]["name"] == "HERBAL_MEDICINE"
    train.tick(g, train.seconds(g, "HERBAL_MEDICINE", "MONASTERY"))
    assert "HERBAL_MEDICINE" in g.techs


def test_after_it_units_in_buildings_heal_6_times_as_fast():
    server, g = setup(("a", "MILITIA", CASTLE, 10.0, 200.0), ("b", "MILITIA", TC, 10.0, 200.0))
    g.techs.add("HERBAL_MEDICINE")
    run(g, 50)
    assert server.entities["a"]["Health"] == pytest.approx(10 + 1.2 * 50)    # 72 HP per minute
    assert server.entities["b"]["Health"] == pytest.approx(10 + 0.6 * 50)    # 36 HP per minute
