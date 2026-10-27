"""The rule tables of bot, cheats, diplomacy, fleet, garrison, monk and replay come from the data files (#2034):
game/data/cheats.jsonl, monk.jsonl, replay.jsonl and keys of the lines of units, buildings, train and build.jsonl."""
import os
import subprocess
import sys

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import cheats  # noqa: E402
import monk  # noqa: E402
import table  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = ("cheats.jsonl", "monk.jsonl", "replay.jsonl")


def test_the_rule_of_a_transform_is_a_function_of_cheats():
    for r in table.load("cheats.jsonl"):
        assert callable(getattr(cheats, r.get("rule", "villager"), None)), r["name"]


def test_the_cheats_make_units_and_transforms_from_the_file():
    assert isinstance(cheats.CODES["catzor"], cheats.Unit)
    camel = cheats.CODES["cameleon"]
    assert camel.units("CAMEL") and not camel.units("MAMELUKE")
    assert cheats.CODES["put on your capes"].units is cheats.infantry


def test_the_monk_rules_keep_their_kinds():
    assert "KING" in monk.IMMUNE and "TREBUCHET" in monk.NEXT and "CASTLE" in monk.LASTING
    assert not set(monk.IMMUNE) & set(monk.LASTING)


def test_the_files_merge_by_name():
    for name in FILES:
        out = subprocess.run(["git", "check-attr", "merge", f"game/data/{name}"], cwd=ROOT, capture_output=True,
                             text=True).stdout
        assert out.strip().endswith("merge: jsonl"), name

