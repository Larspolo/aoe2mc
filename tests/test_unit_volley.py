"""A unit with the key "volley" of data/units.jsonl fires its extra projectiles in each shot (#4502, AoE2 DE wiki
infoboxes "PAttack": the Chu Ko Nu, the Kipchak and the Hussite Wagon): combat.VOLLEY and train.volley_command.
Fake server, test data (a monkeypatched table)."""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
from test_dock_train import dock_map  # noqa: E402

import combat  # noqa: E402  (train imports combat by its plain name: patch that module)
from game import train  # noqa: E402


def test_a_unit_of_the_key_volley_fires_its_extra_projectiles(monkeypatch):
    monkeypatch.setattr(combat, "VOLLEY", {"ARCHER": {"shots": 2, "attack": 3}})
    server, g = dock_map()
    g.data["players"]["1"]["civ"] = "FRANKS"                  # a civilization with no key "volley"
    assert train.volley_command(g, "u", "ARCHER") == "aoe volley u 2 3"
    assert train.volley_command(g, "u", "CROSSBOWMAN") is None
