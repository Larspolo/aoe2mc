"""train.UPGRADES comes from the key "upgrade" of the lines of game/data/train.jsonl (#1915): a new upgrade technology
is one line of the data file, with no literal in game/train.py. The tests check the form of the key, not its values."""
import inspect
import json

from game import train

def test_train_py_has_no_upgrades_literal():
    assert "UPGRADES = {\n" not in inspect.getsource(train)


def test_the_units_of_an_upgrade_are_lists_of_names():
    for line in open(train.DATA, encoding="utf-8"):
        u = json.loads(line).get("upgrade") if line.strip() else None
        pairs = u if u and isinstance(u[0], list) else [u] * bool(u)
        assert all(len(p) == 2 and all(isinstance(n, str) and n.isupper() for n in p) for p in pairs), u
