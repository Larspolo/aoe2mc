"""Block Printing (#1457): the monastery researches it in the Imperial Age (200 gold, 55 s, AoE2 wiki "Block
Printing"), and then a monk converts from 3 tiles farther (9 + 3 tiles)."""
from test_monk_convert import setup
from test_monk_techs import MONASTERY, research
from test_monk_train import monastery

from game import civs, monk, train


def test_the_values_are_those_of_aoe2():
    assert train.COSTS["BLOCK_PRINTING"] == {"gold": 200} and train.TRAIN_TIMES["BLOCK_PRINTING"] == 55
    assert train.TECH_AGE["BLOCK_PRINTING"] == 3 and len(train.HELP["BLOCK_PRINTING"]) <= 50
    assert {"CELTS", "GOTHS", "MONGOLS"} <= set(civs.MISSING["BLOCK_PRINTING"])
    assert "BRITONS" not in civs.MISSING["BLOCK_PRINTING"]


def test_the_monastery_researches_it_only_in_the_imperial_age():
    server, g = monastery(age=2)
    g.stock["gold"] = 200
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 4) == 0 and g.stock["gold"] == 200
    server, g = monastery(age=3)
    rect = research(g, 4, 200)
    assert g.queues[rect][0]["name"] == "BLOCK_PRINTING"
    train.tick(g, 55)
    assert "BLOCK_PRINTING" in g.techs


def test_after_it_a_monk_converts_from_3_tiles_farther():
    server, g = setup(("far", "MILITIA", 2, 5.5 + 11))                # 11 tiles from the monk (tile size 1)
    pos = g.positions(["monk", "far"])
    assert not monk.near(g, "monk", "far", pos)
    g.techs.add("BLOCK_PRINTING")
    assert monk.near(g, "monk", "far", pos)
    server.entities["far"]["Pos"] = (5.5 + 12.5, 64.0, 5.5)
    assert not monk.near(g, "monk", "far", g.positions(["monk", "far"]))   # 12.5 tiles: still too far
