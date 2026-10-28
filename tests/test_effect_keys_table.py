"""#2873: read_scenario takes the keys of each trigger effect from aoe2mc.EFFECT_KEYS, also of the older effects."""
import ast
import inspect

import aoe2mc


class Effect:
    def __getattr__(self, name):
        return f"<{name}>"


def keys(effect_id, **attrs):
    e = Effect()
    vars(e).update(attrs)
    return {k: v(e, {7: "ARCHER"}, {3: "LOOM"}) if callable(v) else getattr(e, v)
            for k, v in aoe2mc.EFFECT_KEYS[effect_id].items()}


def test_read_scenario_has_no_effect_type_entry():
    src = inspect.getsource(aoe2mc.read_scenario)
    tests = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Attribute) and n.attr == "effect_type"]
    assert len(tests) == 3, "put the keys of a new effect into EFFECT_KEYS"   # type=, the table read, "mood"


def test_computed_keys():
    assert keys(aoe2mc.CHANGE_TECHNOLOGY_COST, technology=3, resource_1=0, resource_1_quantity=5,
                resource_2=1, resource_2_quantity=0, resource_3=2, resource_3_quantity=0) == {
        "cost": [[0, 5], [1, 0], [2, 0]], "technology": "LOOM"}
    assert keys(aoe2mc.REPLACE_OBJECT, object_list_unit_id_2=7) == {"target": "<target_player>", "object2": "ARCHER"}
    assert keys(aoe2mc.UNLOAD, selected_object_ids=None) == {"selected": []}
    assert keys(aoe2mc.PLAY_SOUND, sound_name=None) == {"sound": ""}
