"""#2830: each name of data/lines.jsonl (units.LINES) gets its own design: classify() must not catch it with a name
part before line_unit() (the Hoplite got the spear design, not its golden armor)."""
import units


def test_each_line_unit_gets_its_design():
    for n in units.LINES:
        for name in (n, "ELITE_" + n):
            assert units.classify(name) == units.line_unit(name), name

