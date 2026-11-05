"""The marks of the selection box during a left drag (#5761): Drag.java marks the units that game/gather.py
Gather.drag_end selects at the release, by the same rule (military units win over villagers)."""
import re
from pathlib import Path

from test_deselect import paper

from game import lang

DRAG = Path(__file__).parent.parent / "game/plugin/src/main/java/aoe2mc/Drag.java"


def test_the_box_with_villagers_and_military_units_selects_the_military_units():
    server, g = paper()
    g.drag_end("Steve", 2, 8, 13, 13)                                 # m-1, m-2, a-1 and the villager v-1
    assert g.selected == {"m-1", "m-2", "a-1"}


def test_the_box_with_villagers_only_selects_the_villagers():
    server, g = paper()
    g.drag_end("Steve", 14, 2, 10, 6)
    assert g.selected == {"v-1"}


def test_the_marks_of_the_plugin_show_the_counts_of_the_hints():
    keys = set(re.findall(r"\"(aoe2mc\.(?:hints|gather)\.[a-z_]+)\"", DRAG.read_text()))
    keys |= {k + "_many" for k in keys if k.startswith("aoe2mc.hints.count_")}
    assert keys and keys <= lang.en_us().keys()                       # the resource pack translates them
