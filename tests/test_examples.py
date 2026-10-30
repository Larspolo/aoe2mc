"""The example maps in examples/ come from tools/scenarios.py: the maker must give the committed file again."""
import os

import pytest
import scenarios

EXAMPLES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")


@pytest.mark.parametrize("kind", ["river_town", "four_civs", "battle"])
def test_example_is_made_again(kind, tmp_path):
    out = scenarios.MAKERS[kind](str(tmp_path / "out.aoe2scenario"))
    with open(out, "rb") as a, open(os.path.join(EXAMPLES, f"{kind}.aoe2scenario"), "rb") as b:
        assert a.read() == b.read(), f"run: python3 tools/scenarios.py {kind} examples/{kind}.aoe2scenario"
