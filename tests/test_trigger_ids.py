"""The trigger effect and condition constants of aoe2mc.py have the values of EffectId and ConditionId of
AoE2ScenarioParser, not the order of the AoE2 editor menu (#2692)."""
import re

from AoE2ScenarioParser.datasets.conditions import ConditionId
from AoE2ScenarioParser.datasets.effects import EffectId

import aoe2mc


def constants():
    """(name, value, enum member) of each constant with an editor name in its comment, for example
    `HEAL_OBJECT = 34  # "Heal Object" (#2692)`. A constant that matches no member (an attribute) is not a trigger."""
    out = []
    for name, value, comment in re.findall(r'^([A-Z_]+) = (\d+)[ \t]+# (.*"[^"\n]+".*)$', open(aoe2mc.__file__).read(), re.M):
        enum = ConditionId if "condition" in comment else EffectId
        label = re.search(r'"([^"]+)"', comment).group(1).upper().replace(" ", "_")
        member = enum.__members__.get(name) or enum.__members__.get(label)
        if member is not None:
            out.append((name, int(value), member))
    return out


def test_the_scan_finds_the_constants():
    names = {n for n, _, _ in constants()}
    assert {"HEAL_OBJECT", "DECLARE_VICTORY", "RESEARCHED", "TRIGGER_CHANCE"} <= names


def test_each_constant_has_the_parser_value():
    wrong = [f"{n} = {v}, {m!r} is {m.value}" for n, v, m in constants() if v != m.value]
    assert not wrong, "use the values of AoE2ScenarioParser (datasets/effects.py, conditions.py): " + "; ".join(wrong)
