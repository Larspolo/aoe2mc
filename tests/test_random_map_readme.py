"""The kinds of --random-map: the README names each one, and the Highland river works with 4 players (#1945)."""
import re
from pathlib import Path

import numpy as np
import pytest
from test_random_map_highland import reach

import aoe2mc
import rmap

T = rmap.TERRAINS


def kinds():
    """The choices of --random-map in the parser of aoe2mc.py."""
    src = Path(aoe2mc.__file__).read_text()
    choices = re.search(r'"--random-map", choices=\(([^)]*)\)', src).group(1)
    return set(re.findall(r'"(\w+)"', choices))


def test_the_parser_choices_are_the_generators():
    assert kinds() == set(rmap.GENERATORS)


def test_the_readme_names_each_kind():
    text = Path(aoe2mc.__file__).with_name("README.md").read_text()
    section = text.split("## Random map scripts")[1].split("\n## ")[0]
    assert {k for k in kinds() if f"`--random-map {k}`" not in section and f"--random-map {k} " not in section} == set()


@pytest.mark.parametrize("seed", range(1, 11))
def test_the_highland_river_has_fords_and_each_player_reaches_each_other_with_4(seed):
    d = rmap.random_map("highland", seed, 4)
    t = np.array(d["terrain"])
    tcs = [(int(o["x"]), int(o["y"])) for o in d["objects"] if o["name"] == "TOWN_CENTER"]
    assert len(tcs) == 4
    assert (t == T["SHALLOW"]).sum() >= 3 * 7 and (t == T["WATER"]).sum() > 400
    open_land = ~np.isin(t, [T["WATER"]] + list(rmap.FOREST_TREES))       # land without forest, and the fords
    seen = reach(t, tcs[0], open_land)
    assert all(c in seen for c in tcs[1:])
