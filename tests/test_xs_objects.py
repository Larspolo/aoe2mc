"""The unit kind functions of an XS script (game/xs_host.py, #5842): each one reads the data of a unit kind."""
import aoe2mc
from game import combat, train
from tests.test_xs_host import ARCHER, side, value


def test_object_attribute_is_the_combat_value_of_the_player():
    g = side()
    want = train.stats(g, "ARCHER")
    assert value(g, f"xsGetObjectAttribute(1, {ARCHER}, 0, -1)", "float") == float(want.hp)
    assert value(g, f"xsGetObjectAttribute(1, {ARCHER}, 8, 4)", "float") == float(want.melee)
    g.trigger_attributes = [["ARCHER", "hp", 2, 5.0]]                  # a "Modify Attribute" (+5) counts
    assert value(g, f"xsGetObjectAttribute(1, {ARCHER}, 0, -1)", "float") == float(want.hp + 5)


def test_unknown_attribute_or_object_gives_0(capsys):
    assert value(side(), f"xsGetObjectAttribute(1, {ARCHER}, 77, -1)", "float") == 0.0
    assert value(side(), "xsGetObjectAttribute(1, 999999, 0, -1)", "float") == 0.0
    assert "unknown" in capsys.readouterr().err


def test_class_type_and_name():
    from AoE2ScenarioParser.datasets.trigger_lists import ObjectClass, ObjectType
    c = value(side(), f"xsGetObjectClass(1, {ARCHER})")
    assert train.applies(f"@{ObjectClass(c).name.lower()}", "ARCHER")
    assert value(side(), f"xsGetObjectType(1, {ARCHER})") == ObjectType.MILITARY.value
    house = next(i for i, (p, _) in aoe2mc.object_kinds().items() if p == "B")
    assert value(side(), f"xsGetObjectType(1, {house})") == ObjectType.BUILDING.value
    assert value(side(), f"xsGetObjectName({ARCHER}, 1, true)", "string") == "ARCHER"
    assert value(side(), f"xsGetObjectName({ARCHER})", "string") == "Archer"
    assert "ARCHER" in combat.STATS


def test_enum_names():
    from AoE2ScenarioParser.datasets.trigger_lists import Attribute, DamageClass, ObjectAttribute
    assert value(side(), "xsGetObjectAttributeName(0)", "string") == ObjectAttribute(0).name
    assert value(side(), "xsGetDamageClassName(4)", "string") == DamageClass(4).name
    assert value(side(), "xsGetPlayerAttributeName(0, true)", "string") == Attribute(0).name.replace("_", " ").title()
    assert value(side(), "xsGetDamageClassName(-5)", "string") == ""


def test_task_amounts():
    g = side()
    assert value(g, "xsGetTaskAmount(3)", "float") == 0.0
    from game import xs_host
    from game.xs_run import Xs
    x = Xs("float a = 0; float b = 0; void main() { xsTaskAmount(3, 2.5); a = xsGetTaskAmount(3);"
           " xsResetTaskAmount(); b = xsGetTaskAmount(3); }", out=print, host=xs_host.host(g))
    x.tick(0)
    assert (x.get("a"), x.get("b")) == (2.5, 0.0)
