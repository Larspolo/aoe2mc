"""cliff_type in <CLIFF_GENERATION>: the cliff objects of the type (#3852)."""
import pytest
from test_rms_cliffs import CLIFFS

import rmap


def cliffs(text, warn=lambda m: pytest.fail(m)):
    return [o["name"] for o in rmap.generate(text, 3, size=120, warn=warn)["objects"] if o["name"].startswith("CLIFF")]


@pytest.mark.parametrize("kind", ["CLIFF_DESERT", "CLIFF_SNOW"])
def test_a_cliff_type_gives_only_its_cliffs(kind):
    names = cliffs(CLIFFS + f"cliff_type {kind}\n")
    assert names and all(n.startswith(kind + "_") for n in names)


def test_no_cliff_type_gives_default_cliffs():
    names = cliffs(CLIFFS)
    assert names and all(n.startswith("CLIFF_DEFAULT_") for n in names)


def test_an_unknown_cliff_type_warns_and_gives_default_cliffs():
    said = []
    names = cliffs(CLIFFS + "cliff_type CLIFF_LAVA\n", said.append)
    assert any("CLIFF_LAVA" in m for m in said) and all(n.startswith("CLIFF_DEFAULT_") for n in names)
