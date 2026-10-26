"""game/train.py: a complete own castle adds 20 to the population limit, as in AoE2 (#695)."""
from test_train_population import setup

from game import train


def test_a_castle_adds_20_to_the_limit():
    _, g = setup()
    g.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 1, "tile": [15, 5],
                              "footprint": [13, 3, 17, 7]})
    g.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 2, "tile": [15, 15],
                              "footprint": [13, 13, 17, 17]})
    assert train.limit(g) == 25                                        # the town center and the own castle
