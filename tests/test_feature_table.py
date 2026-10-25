"""tools/feature_table.py writes the column "Used today in" of the feature table in docs/DESIGN.md (#234)."""
from collections import Counter

import feature_table as ft

TABLE = """## 2. Real blocks

| AoE2 feature | Minecraft block | Used today in |
|---|---|---|
| Archery target | `target` | `old_name` |
| Millstone | `grindstone` | |
| Terracotta roof | `brick` stairs |
| Rose window | `*_stained_glass_pane` | `monastery` |

Text after the table.
"""


def test_patterns():
    assert ft.patterns("`brick` stairs, `*_log[axis=x]` and `Canvas.flag`") == [["brick", "brick_stairs"], ["*_log"]]


def test_column_ranks_and_filters():
    use = {"a": Counter(gold_ore=5, cobblestone=50, stone=5), "b": Counter(cobblestone=900, bricks=100),
           "c": Counter(gold_ore=1, spruce_planks=99)}
    assert ft.column("`gold_ore`, `cobblestone`, `stone`", use) == "`a`"      # b uses 1 of 3 names, a uses 3
    assert ft.column("`gold_ore`", use) == "`a`, `c`"                         # share of the blocks: a 8 %, c 1 %
    assert ft.column("`melon`", use) == "no design"
    ft.SHOW, show = 1, ft.SHOW
    try:
        assert ft.column("`gold_ore`", use) == "`a` +1 more"
    finally:
        ft.SHOW = show


def test_rewrite_with_designs():
    use = ft.usage(only={"ARCHERY_RANGE", "MILL"})
    assert {"archery_range", "mill", "granary"} <= set(use)                  # granary: mill of the flat-roof sets
    text = ft.rewrite(TABLE, use)
    assert "| Archery target | `target` | `archery_range` |" in text
    assert "| Millstone | `grindstone` | " in text and "`mill`" in text.split("Millstone")[1].split("\n")[0]
    assert "| Rose window | `*_stained_glass_pane` | no design |" in text
    assert text.startswith("## 2. Real blocks\n") and text.endswith("Text after the table.\n")
    assert len(text.split("\n")) == len(TABLE.split("\n"))
