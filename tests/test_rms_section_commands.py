"""color_correction, effect_amount and effect_percent in each section of a DE script (#5073)."""
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
def test_color_correction_in_each_section(section):   # a name of aoe2mc.MOODS
    mood = "AUTUMN"
    out, warns = run(section, f"color_correction CC_{mood}")
    assert out["mood"] == mood
    assert warns == []


@pytest.mark.parametrize("section", ALL)
@pytest.mark.parametrize("cmd", ["effect_amount SET_ATTRIBUTE VILLAGER_CLASS 1 5",
                                 "effect_percent MUL_ATTRIBUTE VILLAGER_CLASS 1 50"])
def test_effect_in_each_section(section, cmd):
    assert run(section, cmd)[1] == []
