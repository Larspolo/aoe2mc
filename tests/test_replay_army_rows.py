"""Live replay: the army rows show only military units in training (#3818, #3924)."""

from test_replay_army_view import make
from test_replay_stat_books import page


def test_a_villager_in_training_does_not_show_and_a_military_unit_does():
    r = make([{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
              {"time": 0, "player": 1, "kind": "queue", "type": 93, "objects": [5], "name": "SPEARMAN"}])
    assert page(r.army_view(500), 0)[1] == "Training: 1 Spearman"
