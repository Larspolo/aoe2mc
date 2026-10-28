"""#3396: each aggressive animal of data/animals.jsonl has its AoE2 combat values in game/data/units.jsonl."""
import json
import os

from game import combat

ROOT = os.path.join(os.path.dirname(__file__), "..")


def aggressive_keys():
    with open(os.path.join(ROOT, "data", "animals.jsonl"), encoding="utf-8") as f:
        return [k for line in f if json.loads(line).get("behavior") == "aggressive" for k in json.loads(line)["keys"]]


def test_every_aggressive_animal_has_combat_values():
    keys = aggressive_keys()
    missing = [k for k in keys if k not in combat.STATS]
    assert not missing, f"no line in game/data/units.jsonl for {missing}"


def test_predator_values_are_positive():
    for k in aggressive_keys():
        s = combat.stats(k)
        assert s.hp > 0 and s.attack > 0 and s.reload > 0, k
