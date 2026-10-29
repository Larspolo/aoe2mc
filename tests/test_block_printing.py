"""Block Printing (#1457): the monastery researches it in the Imperial Age (AoE2 wiki "Block Printing"), and
then a monk converts from 3 tiles farther (9 + 3 tiles)."""
from test_monk_convert import setup
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import monk, train

SLOT = train.ITEMS["BLOCK_PRINTING"][0]


def test_the_monastery_researches_it_only_in_the_imperial_age():
    server, g = monastery(age=2)
    gold = train.price(g, "BLOCK_PRINTING")["gold"]
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, SLOT) == 0 and g.stock["gold"] == gold
    server, g = monastery(age=3)
    rect = research(g, SLOT, gold)
    assert g.queues[rect][0]["name"] == "BLOCK_PRINTING"
    train.tick(g, train.TRAIN_TIMES["BLOCK_PRINTING"])
    assert "BLOCK_PRINTING" in g.techs


def test_after_it_a_monk_converts_from_3_tiles_farther():
    server, g = setup(("far", "MILITIA", 2, 5.5 + 11))                # 11 tiles from the monk (tile size 1)
    pos = g.positions(["monk", "far"])
    assert not monk.near(g, "monk", "far", pos)
    g.techs.add("BLOCK_PRINTING")
    assert monk.near(g, "monk", "far", pos)
    server.entities["far"]["Pos"] = (5.5 + 12.5, 64.0, 5.5)
    assert not monk.near(g, "monk", "far", g.positions(["monk", "far"]))   # 12.5 tiles: still too far
