"""The hit points of a mounted unit are on its mount, where the game program keeps them (#2976): the condition
"Object HP" and the effects Damage Object, Heal Object, Change Object HP and Modify Object Attribute by Variable."""
import json
from collections import Counter

import numpy as np
import pytest

import aoe2mc
import units

AREA = [2, 3, 4, 5]


def effect(kind, name=None, **keys):
    return dict(type=kind, message="", player=1, time=0, object=("U", name) if name else None, tile=[-1, -1],
                area=AREA, **keys)


def build(effects=(), conditions=None):
    t = dict(id=7, name="t", enabled=True, looping=False,
             conditions=conditions or [dict(type=aoe2mc.TIMER, timer=30, inverted=False)], effects=list(effects))
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16), {1: {"color": "blue"}}, Counter())[1]


def lines(effects):
    return build(effects).get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


HP_EFFECTS = [effect(aoe2mc.DAMAGE_OBJECT, "KNIGHT", quantity=30),
              effect(aoe2mc.DAMAGE_OBJECT, "KNIGHT", quantity=-30),                  # a heal
              effect(aoe2mc.HEAL_OBJECT, "KNIGHT", quantity=30),
              effect(aoe2mc.CHANGE_OBJECT_HP, "KNIGHT", operation=1, quantity=50),
              effect(aoe2mc.CHANGE_OBJECT_HP, "KNIGHT", operation=2, quantity=50),
              effect(aoe2mc.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE, "KNIGHT", operation=2, attribute=0, variable=3)]


@pytest.mark.parametrize("e", HP_EFFECTS, ids=["damage", "negative damage", "heal", "hp set", "hp add", "by variable"])
def test_the_hp_effects_of_a_knight_act_on_its_horse(e):
    found = lines([e])
    assert found and all(" on vehicle " in line for line in found)              # the rider has no AoE2 hit points
    assert all("predicate" not in line for line in found)                      # the type says that it rides


@pytest.mark.parametrize("name", ["MILITIA", "MANGONEL"])
def test_a_unit_on_foot_and_a_siege_unit_keep_acting_on_the_tagged_entity(name):
    for e in HP_EFFECTS:
        found = lines([{**e, "object": ("U", name)}])
        assert found and not any("vehicle" in line for line in found)          # the crew of a minecart has them


def test_with_no_type_the_predicate_splits_riders_and_units_on_foot():
    files = build([effect(aoe2mc.DAMAGE_OBJECT, quantity=30)])
    foot, ride = files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines()
    assert foot.startswith("execute as @e[tag=aoe2mc.p1,") and foot.endswith(" unless predicate aoe2mc:rider run damage @s 30")
    assert ride.endswith(" if predicate aoe2mc:rider on vehicle run damage @s 30")
    rider = files["data/aoe2mc/predicate/rider.json"]
    assert rider["type"] == "minecraft:entity_properties"                     # 26.3: "type", not "condition"
    assert rider["predicate"] == {"minecraft:vehicle": {"minecraft:entity_type": list(units.MOUNTS)}}   # 26.3 keys
    assert "minecraft:minecart" not in units.MOUNTS                           # a siege unit keeps them on its crew


def test_the_object_hp_condition_reads_the_health_of_the_mount():
    files = build([{**effect(aoe2mc.SEND_CHAT), "message": "Hurt", "area": [-1] * 4}],
                  [dict(type=aoe2mc.OBJECT_HP, timer=0, ref=7, quantity=50, comparison=1, inverted=False)])
    text = "\n".join(v for v in files.values() if isinstance(v, str))
    assert "execute as @e[tag=aoe2mc.r7,limit=1] if predicate aoe2mc:rider on vehicle store result score " in text
    assert "execute as @e[tag=aoe2mc.r7,limit=1] unless predicate aoe2mc:rider store result score " in text
    assert "data get entity @e[tag=aoe2mc.r7" not in text                      # not the 20 Health of the rider
    json.dumps(files["data/aoe2mc/predicate/rider.json"])


def test_each_mount_of_the_units_is_in_mounts():
    rng = np.random.default_rng(0)
    for name in ("KNIGHT", "CAMEL_RIDER", "CAVALRY_ARCHER", "STEPPE_LANCER"):
        nbt = units.make_entity(dict(name=name, player=1), {}, (0.0, 0.0, 0.0), rng)
        assert units.top_entity(nbt) is not nbt and str(nbt["id"]) in units.MOUNTS


@pytest.mark.mc
def test_damage_object_on_a_knight_hurts_its_horse_on_a_server(tmp_path):
    import os
    import re
    import time

    from test_paper import paper_reachable
    from game import run
    from tools import scenarios
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = str(tmp_path / "W")
    aoe2mc.convert(scenarios.tiny(str(tmp_path / "t.aoe2scenario")), world)
    files = build([effect(aoe2mc.DAMAGE_OBJECT, quantity=6), effect(aoe2mc.DAMAGE_OBJECT, "KNIGHT", quantity=4)])
    for path, data in files.items():
        dst = os.path.join(world, "datapacks", "aoe2mc", path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
    with run.Game(world) as game:
        game.forceload()
        game.command("time set midnight")                                    # no zombie burns
        game.command('summon horse 10 70 14 {Tame:1b,Tags:["aoe2mc.hph"],Passengers:[{id:"minecraft:zombie",'
                     'Tags:["aoe2mc.p1","aoe2mc.hpr","aoe2mc.t38"]}]}')

        def health(tag):
            return float(re.findall(r"([\d.]+)f", game.command(f"data get entity @e[tag={tag},limit=1] Health"))[0])
        horse, rider = health("aoe2mc.hph"), health("aoe2mc.hpr")
        for line in files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines():
            game.command(line)
            time.sleep(1)                                                        # after the hurt time of the horse
        assert health("aoe2mc.hpr") == rider                                    # the rider keeps its Health
        assert health("aoe2mc.hph") <= horse - 9                                # 6 with no type, then 4 as a KNIGHT
