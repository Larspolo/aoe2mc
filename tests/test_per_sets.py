"""game/per.py: the count facts by the airef unit sets and classes (#5104): monk-set, the villager sets by work, the
classes of per_classes.jsonl."""
from test_per_counts import script

from game import per

SETS = [n for n, r in per.names().items() if n.endswith("-set") or n.startswith("villager-") and r["kind"] == "unit"]
CLASSES = ["farm-class", "relic-class", "shore-fish-class", "cavalry-archer-class", "wall-class", "warship-class",
           "all-units-class"]


def test_villager_sets(capsys):
    s, b, me = script()
    n = len(b.g.villagers)
    assert s.check(("unit-type-count", "villager-base", "==", n))
    assert s.check(("unit-type-count", "villager-farmer", ">=", 0)) and s.check(("unit-type-count", "monk-set", "==", 0))
    v = next(iter(b.g.villagers.values()))
    v.task = "LUMBERJACK"
    assert s.check(("unit-type-count", "villager-wood", "==", 1))
    assert s.check(("unit-type-count", "all-units-class", "==", n + 2))
    assert "unknown" not in capsys.readouterr().err


def test_no_set_or_class_is_unknown(capsys):
    s, b, me = script()
    assert len(SETS) >= 21
    for name in SETS + CLASSES:
        row = per.names().get(name, {})
        s.check(("building-type-count" if row.get("kind") == "building" else "unit-type-count", name, ">=", 0))
    s.check(("building-type-count", "wall-class", ">=", 0))
    assert "unknown" not in capsys.readouterr().err
