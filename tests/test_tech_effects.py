"""The effect of each technology is its key "effect" in game/data/train.jsonl, not a lambda in game/train.py (#2029)."""
from game import combat, train

FIELDS = set(combat.Stats._fields)
TESTS = {"class", "names", "prefix", "forms", "test"}


def test_each_effect_has_a_known_form():
    for r in train.ROWS:
        e = r.get("effect")
        if isinstance(e, str):
            assert callable(getattr(train, e, None)), r["name"]
        for e in [] if isinstance(e, str) or e is None else e if isinstance(e, list) else [e]:   # a list: #2155
            assert set(e) <= {"if", "add", "times", "bonus", "bonus_times"}, r["name"]
            assert set(e.get("add", {})) | set(e.get("times", {})) <= FIELDS - {"bonus", "classes"}, r["name"]
            for t in e.get("if", []):
                assert len(t) == 1 and set(t) <= TESTS, r["name"]
                assert "test" not in t or callable(getattr(train, t["test"], None)), r["name"]


def test_an_effect_changes_only_the_units_of_its_tests():
    rows = {"add": {"if": [{"class": "infantry"}], "add": {"attack": 2}, "bonus": {"cavalry": 3}},
            "times": {"if": [{"names": ["CASTLE"]}], "times": {"hp": 1.5}}}
    add, times = (train.effect(e) for e in rows.values())
    militia, archer, castle = (combat.stats(n) for n in ("MILITIA", "ARCHER", "CASTLE"))
    assert add("MILITIA", militia) == militia._replace(attack=militia.attack + 2,
                                                       bonus={**militia.bonus, "cavalry": militia.bonus.get("cavalry", 0) + 3})
    assert add("ARCHER", archer) == archer and times("ARCHER", archer) == archer
    assert times("CASTLE", castle).hp == round(castle.hp * 1.5)
    assert train.effect({})("ARCHER", archer) == archer
    assert train.effect("fletching") is train.fletching
