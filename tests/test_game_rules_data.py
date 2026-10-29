"""The rule tables of bot, cheats, diplomacy, fleet, garrison, monk and replay come from the data files (#2034):
game/data/cheats.jsonl, monk.jsonl, replay.jsonl and keys of the lines of units, buildings, train and build.jsonl."""
import os
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import cheats  # noqa: E402
import monk  # noqa: E402
import table  # noqa: E402


def test_the_rule_of_a_transform_is_a_function_of_cheats():
    for r in table.load("cheats.jsonl"):
        assert callable(getattr(cheats, r.get("rule", "villager"), None)), r["name"]


def test_the_cheats_make_units_and_transforms_from_the_file():
    for r in table.load("cheats.jsonl"):
        code = cheats.CODES[r["name"]]
        if "unit" in r:
            assert isinstance(code, cheats.Unit), r["name"]
        elif "rule" in r:
            assert code.units is getattr(cheats, r["rule"]), r["name"]
        else:
            assert all(code.units(n) for n in r["units"]) and not code.units("NO_SUCH_UNIT"), r["name"]


def test_the_monk_rules_keep_their_kinds():
    assert not set(monk.IMMUNE) & set(monk.LASTING)
