"""game/civs.py: an item that few civilizations have names them in the key "civs" of its line in data/train.jsonl or
data/build.jsonl (#2235), an item that most have names the others in the key "not_civs" there (#3200). civs.MISSING
joins the two forms."""
from game import civs

CIVS = {r["name"] for r in civs.ROWS}


def test_missing_joins_the_not_civs_and_the_civs_keys_for_each_name():
    for t, cs in civs.MISSING.items():
        assert set(cs) == {c for c in CIVS if c in civs.NOT.get(t, ()) or c not in civs.ONLY.get(t, {c})}, t
        assert cs and set(cs) < CIVS, t                                    # some have it, some do not
