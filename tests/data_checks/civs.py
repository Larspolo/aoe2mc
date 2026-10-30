"""game/data/civs.jsonl: the bonuses of a civilization (#1914)."""
from game import build, civs, combat, train

from . import NAMES, NUMBER, RES, form


def check(row):
    form(row, {"name": str}, {"unique": str})
    for k, v in row.items():                               # a rule, not a list of keys: parallel tickets add keys (#2239)
        assert isinstance(v, (dict, list, str, int, float)) and not isinstance(v, bool), (row["name"], k, v)
    n = row["name"]
    assert set(row.get("drop", {})) <= {"food", "forage"} and all(isinstance(v, NUMBER) for v in row.get("drop", {}).values()), n
    assert "missing" not in row, n              # the key "not_civs" of the item line (#3200): one line for a new item
    assert row.get("unique", "MILITIA") in NAMES["units.jsonl"], n
    assert set(row.get("twice", ())) <= NAMES["train.jsonl"], n
    assert len(row.get("hp_age", [1] * 4)) == 4 and all(isinstance(a, NUMBER) and a > 0 for a in row.get("hp_age", ())), n
    for t, group in row.get("also", {}).items():                   # one more group gets the effect (#2173)
        assert group in civs.GROUPS and isinstance(train.BY_KEY["effect"].get(t, {}), dict) and t in train.TECHS | train.BY_KEY["walk"], (n, t)
    assert all(t in train.TECHS and isinstance(f, NUMBER) for t, f in row.get("more", {}).items()), n
    for key in ("housing", "sight"):                                    # building -> number (#2118)
        assert set(row.get(key, {})) <= NAMES["buildings.jsonl"] and all(type(v) is int for v in row.get(key, {}).values()), n
    assert len(row.get("pop_cap", (0, 0))) == 2, n
    for group, value, ages in row.get("units", ()):
        classes = {f"bonus:{c}" for t in (*combat.STATS.values(), *combat.BUILDINGS.values()) for c in t.classes}
        assert group in civs.GROUPS and value in (*combat.Stats._fields, "friendly", "speed", "taken", *classes), (n, group, value)   # (#2249)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, group)
    for what, ages in row.get("arrows", ()):                 # the factor of the base arrows of buildings (#2178)
        assert set(what) <= NAMES["buildings.jsonl"] and len(ages) == 4 and all(isinstance(a, int) for a in ages), n
    for what, res, ages in row.get("costs", ()):
        names = NAMES["train.jsonl"] | set(build.COSTS)
        if isinstance(what, list):
            assert set(what) <= names, (n, what)
        else:                                              # a rule of civs.has that covers at least one name
            assert any(civs.has(what, x) for x in sorted(names | NAMES["units.jsonl"])), (n, what)
        assert res is None or res in RES, (n, what, res)
        assert len(ages) == 4 and all(isinstance(a, NUMBER) for a in ages), (n, what)
    for group, buildings, each, most in row.get("cost_per", ()):     # #2177
        assert group in civs.GROUPS and set(buildings) <= NAMES["buildings.jsonl"] and 0 < each <= most < 1, n
