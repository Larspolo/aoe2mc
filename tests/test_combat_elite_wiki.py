"""The elite unique units of game/combat.py (#1075) are never weaker than their base units (#1041). Their values are
lines of game/data/units.jsonl (tests/test_data_files.py, #1916)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402

S = combat.STATS


def test_an_elite_unit_is_never_weaker_than_its_base_unit():
    for name, s in S.items():
        if name.startswith("ELITE_") and (b := S.get(name.removeprefix("ELITE_"))):
            assert s.hp >= b.hp and s.attack >= b.attack and s.reload <= b.reload, name
