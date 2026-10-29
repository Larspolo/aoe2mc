"""#2887 (epic #2538): the trigger effects "Store Key Value", "Load Key Value" and "Delete Key". The value of the
variable #vN of aoe_var stays under a text key in the data storage aoe2mc:keys (only in the world: AoE2 keeps the keys
between the scenarios of a campaign)."""
import contextlib
import io
from collections import Counter

import aoe2mc
from tools import scenarios

PATH = 'storage aoe2mc:keys values."gold left"'


def effect(kind, key="gold left", variable=1, quantity=5):
    return dict(type=kind, message=key, player=-1, time=0, object=None, tile=[-1, -1], area=[-1] * 4,
                variable=variable, quantity=quantity)


def convert(*effects):
    stats = Counter()
    trig = dict(id=3, name="t", enabled=True, looping=False, effects=list(effects),
                conditions=[dict(type=aoe2mc.TIMER, timer=1, inverted=False)])
    load, files = aoe2mc.trigger_files([trig], stats=stats)
    return load, files.get("data/aoe2mc/function/trigger/3.mcfunction", "").splitlines(), stats


def test_store_load_and_delete_give_the_storage_commands():
    load, found, stats = convert(effect(aoe2mc.STORE_KEY_VALUE), effect(aoe2mc.LOAD_KEY_VALUE),
                                 effect(aoe2mc.DELETE_KEY, variable=-1))
    assert found == [f"execute store result {PATH} int 1 run scoreboard players get #v1 aoe_var",
                     "scoreboard players set #v1 aoe_var 5",
                     f"execute if data {PATH} store result score #v1 aoe_var run data get {PATH}",
                     f"data remove {PATH}"]
    assert "scoreboard players add #v1 aoe_var 0" in load               # the variable exists before the store
    assert stats == Counter({"store key value": 1, "load key value": 1, "delete key": 1})


def test_the_quotes_of_the_key_are_escaped():
    _, found, _ = convert(effect(aoe2mc.DELETE_KEY, key='a "b" \\c'))
    assert found == ['data remove storage aoe2mc:keys values."a \\"b\\" \\\\c"']


def test_no_variable_or_an_empty_key_is_not_supported():
    _, found, stats = convert(effect(aoe2mc.STORE_KEY_VALUE, variable=-1), effect(aoe2mc.LOAD_KEY_VALUE, key=" "),
                              effect(aoe2mc.DELETE_KEY, key=""))
    assert found == []
    assert stats == Counter({"store key value (not supported)": 1, "load key value (not supported)": 1,
                             "delete key (not supported)": 1})


def test_read_scenario_keeps_the_variable_the_key_and_the_default(tmp_path):
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Keys")
    t.new_condition.timer(timer=1)
    t.new_effect.load_key_value(variable=1, message="gold left", quantity=5)
    t.new_effect.store_key_value(variable=1, message="gold left")
    src = scenarios.save(scn, str(tmp_path / "k.aoe2scenario"))
    with contextlib.redirect_stdout(io.StringIO()):
        trigger, = aoe2mc.read_scenario(src)[4]["triggers"]
    load, store = trigger["effects"]
    assert (load["variable"], load["message"], load["quantity"]) == (1, "gold left", 5)
    assert (store["variable"], store["message"]) == (1, "gold left")

