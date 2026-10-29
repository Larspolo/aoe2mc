"""game/train.py: a complete own castle adds its housing (train.HOUSING) to the population limit, as in AoE2 (#695)."""
from test_train_population import setup

from game import train


def test_a_castle_adds_its_housing_to_the_limit():
    _, g = setup()
    before = train.limit(g)
    g.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 1, "tile": [15, 5],
                              "footprint": [13, 3, 17, 7]})
    g.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 2, "tile": [15, 15],
                              "footprint": [13, 13, 17, 17]})
    assert train.limit(g) == before + train.HOUSING["CASTLE"]          # only the own castle
