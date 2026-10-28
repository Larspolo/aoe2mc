"""game/civs.py: an item that few civilizations have names them in the key "civs" of its line in data/train.jsonl or
data/build.jsonl, not in the "missing" list of each other civilization line (#2235). civs.MISSING joins the two forms."""
from game import civs, train

CIVS = {r["name"] for r in civs.ROWS}


def test_missing_joins_the_missing_lists_and_the_civs_key_for_each_name():
    rows = {r["name"]: r for r in civs.ROWS}
    for t, cs in civs.MISSING.items():
        assert set(cs) == {c for c, r in rows.items() if t in r["missing"] or c not in civs.ONLY.get(t, {c})}, t
        assert cs and set(cs) < CIVS, t                                    # some have it, some do not


def test_the_values_are_as_before_the_move():
    assert set(civs.MISSING["KREPOST"]) == CIVS - {"BULGARIANS"}                     # build.jsonl
    assert set(civs.MISSING["FORTIFIED_CHURCH"]) == CIVS - set(civs.ONLY["FORTIFIED_CHURCH"]) and \
        len(civs.ONLY["FORTIFIED_CHURCH"]) == 2
    assert set(civs.ELEPHANTS) == {"BENGALIS", "BURMESE", "DRAVIDIANS", "KHMER", "MALAY", "VIETNAMESE"}   # train.jsonl
    assert "VIKINGS" in civs.MISSING["HUSBANDRY"] and "BRITONS" not in civs.MISSING["HUSBANDRY"]   # civs.jsonl
    assert set(train.civs.MISSING["SLINGER"]) == CIVS - {"INCAS", "MAPUCHE", "MUISCA", "TUPI"}
