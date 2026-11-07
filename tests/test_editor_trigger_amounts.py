"""The amounts, classes and option texts of trigger effects in the editor (#6113): Modify Attribute and its kin set
the amount (quantity), or the class and amount of an armor or attack attribute, as Create Object Armor and Create
Object Attack; Create Decision sets its option texts with books. The save has the values."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from AoE2ScenarioParser.datasets.trigger_lists.object_attribute import ObjectAttribute  # noqa: E402
from test_editor_palette import state_of  # noqa: E402
from test_editor_trigger_fields import add, slot  # noqa: E402
from test_editor_trigger_types import click, opened  # noqa: E402
from test_editor_triggers_menu import saved, world_of  # noqa: E402


def test_hit_points_amount_is_saved(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    for name in ("MODIFY_ATTRIBUTE", "MODIFY_ATTRIBUTE_FOR_CLASS", "MODIFY_OBJECT_ATTRIBUTE"):
        e = add(s, at, "effect", name)
        e.object_attributes = ObjectAttribute.HIT_POINTS
        editor.fields_menu(s, "p", at, len(editor.parts(s.scenario.trigger_manager.triggers[at])) - 1)
        names = [a for a, _ in editor.fields("effect", e)]
        assert "quantity" in names and "armour_attack_class" not in names
        click(s, slot("effect", e, "quantity"), shift=True)
        assert e.quantity == 9
    t = saved(s, tmp_path).trigger_manager.triggers[at]
    assert [x.quantity for x in t.effects[-3:]] == [9, 9, 9]


def test_armor_and_attack_class_and_amount_are_saved(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    for name in ("MODIFY_ATTRIBUTE", "CREATE_OBJECT_ARMOR", "CREATE_OBJECT_ATTACK"):
        e = add(s, at, "effect", name)
        if name == "MODIFY_ATTRIBUTE":
            e.object_attributes = ObjectAttribute.ARMOR
        editor.fields_menu(s, "p", at, len(editor.parts(s.scenario.trigger_manager.triggers[at])) - 1)
        assert "quantity" not in [a for a, _ in editor.fields("effect", e)]
        click(s, slot("effect", e, "armour_attack_class"))
        click(s, slot("effect", e, "armour_attack_class"))
        click(s, slot("effect", e, "armour_attack_quantity"), shift=True)
        assert e.armour_attack_quantity == 10 and e.armour_attack_class not in (None, [])
    want = [(x.armour_attack_class, x.armour_attack_quantity) for x in s.scenario.trigger_manager.triggers[at].effects[-3:]]
    t = saved(s, tmp_path).trigger_manager.triggers[at]
    assert [(x.armour_attack_class, x.armour_attack_quantity) for x in t.effects[-3:]] == want


def test_decision_option_texts_are_saved(tiny_world, tmp_path):
    s = state_of(world_of(tiny_world, tmp_path))
    at, _ = opened(s)
    e = add(s, at, "effect", "CREATE_DECISION")
    for a, text in (("message_option1", "Yes"), ("message_option2", "No")):
        s.command = lambda c, a=a, text=text: (f'p has the following entity data: [{{raw:"{text}"}}]'   # noqa: E731
                                               if c.startswith("data get") and a in c else "")
        click(s, slot("effect", e, a))
        editor.read_books(s)
        assert getattr(e, a) == text
    t = saved(s, tmp_path).trigger_manager.triggers[at]
    assert (t.effects[-1].message_option1, t.effects[-1].message_option2) == ("Yes", "No")
