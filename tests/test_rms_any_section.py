"""enable_waves, water_definition and ai_info_map_type in each section of a DE script (#5249)."""
import numpy as np
import pytest

import rmap

ALL = ("HEADER",) + tuple(rmap.SECTIONS)


def run(section, line):
    parts = {s: "" for s in rmap.SECTIONS}
    parts["LAND_GENERATION"] = "base_terrain GRASS\n"
    if section == "HEADER":
        head = line + "\n"
    else:
        head = ""
        parts[section] += line + "\n"
    text = head + "".join(f"<{s}>\n{b}" for s, b in parts.items())
    warns = []
    return rmap.generate(text, 1, size=40, warn=warns.append), warns


@pytest.mark.parametrize("section", ALL)
@pytest.mark.parametrize("cmd", ["enable_waves 1", "water_definition WATER", "ai_info_map_type ARABIA 0 0 0"])
def test_any_section_gives_no_warning(section, cmd):
    assert run(section, cmd)[1] == []


@pytest.mark.parametrize("section", ALL)
@pytest.mark.parametrize("cmd", ["enable_waves 1", "water_definition WATER", "ai_info_map_type ARABIA 0 0 0"])
def test_the_map_does_not_change(section, cmd):
    base = run(section, "")[0]
    out = run(section, cmd)[0]
    assert np.array_equal(out["terrain"], base["terrain"])
