"""#3083 (epic #2538): the trigger effects "Change Object Attack", "Change Object Armor", "Change Object Speed" and
"Change Object HP" tag their units and store a value order in the data storage aoe2mc:orders; the scenario mode of the
game program keeps the new values of each unit, and later technologies and orders keep them."""
import numpy as np
import pytest

import aoe2mc
from test_scenario_patrol import scenario, trigger
from test_scenario_mode import game

from game import ai, combat, gather, train


def lines(*effects):
    t = trigger(*[e["type"] for e in effects])
    for f, e in zip(t["effects"], effects):
        f.update(e)
    return aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1].get(
        "data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def unit_value(line):
    """True for a line of the value order of the game program (aoe2mc.value_lines): the tests of the attributes leave
    them out."""
    return "aoe_order" in line or "aoe2mc:value" in line


def orders(out):
    return [x.split(" value ", 1)[1] for x in out if x.startswith("data modify storage aoe2mc:orders")]


def test_the_four_effects_store_value_orders_and_keep_their_attribute_commands():
    out = lines(dict(type=aoe2mc.CHANGE_OBJECT_ATTACK, operation=2, quantity=2, armour_class=4),
                dict(type=aoe2mc.CHANGE_OBJECT_ARMOR, operation=2, quantity=1, armour_class=3),
                dict(type=aoe2mc.CHANGE_OBJECT_SPEED, quantity=2),
                dict(type=aoe2mc.CHANGE_OBJECT_HP, operation=1, quantity=200))
    assert orders(out) == ['"value aoe_order7_0 attack 2 2"', '"value aoe_order7_1 pierce 2 1"',
                           '"value aoe_order7_2 speed 1 2"', '"value aoe_order7_3 hp 1 200"']
    assert any(" add aoe_order7_0" in x and x.startswith("tag @e[tag=aoe2mc.p1,") for x in out)
    for attribute in ("attack_damage modifier add aoe2mc:trig_7_0 2", "armor modifier add aoe2mc:trig_7_1 1",
                      "movement_speed base set", "max_health base set 200"):
        assert any(attribute in x for x in out), attribute


def test_an_armor_of_another_class_keeps_only_its_attribute_command():
    out = lines(dict(type=aoe2mc.CHANGE_OBJECT_ARMOR, operation=2, quantity=1, armour_class=11))
    assert orders(out) == [] and any("minecraft:armor modifier add" in x for x in out)


def test_modify_object_attribute_stores_the_same_order():
    out = lines(dict(type=aoe2mc.MODIFY_OBJECT_ATTRIBUTE, attribute=9, operation=3, aa=1, armour_class=3))
    assert orders(out) == ['"value aoe_order7_0 attack 3 1"']


def test_modify_object_attribute_by_variable_stores_the_order_with_the_score():
    t = trigger(aoe2mc.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE)
    t["effects"][0].update(attribute=0, operation=2, variable=3)
    files = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1]
    out = files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines()
    assert any(x.startswith("tag @e[tag=aoe2mc.p1,") and x.endswith(" add aoe_order7_0") for x in out)
    assert "execute store result storage aoe2mc:value value int 1 run scoreboard players get #v3 aoe_var" in out
    assert out[-1] == "function aoe2mc:value with storage aoe2mc:value"
    assert files["data/aoe2mc/function/value.mcfunction"] == \
        '$data modify storage aoe2mc:orders list append value "value $(tag) $(field) $(op) $(value)"\n'


def run(*stored, tagged=("m1",)):
    """scenario.orders with the stored orders: an own militia m1 and an own archer a1; the units in tagged have the
    tag of each order."""
    server, g, _ = game({"1": {}, "2": {}})
    g.soldiers.update({"m1": "MILITIA", "a1": "ARCHER"})
    command, got = server.command, ["Storage aoe2mc:orders has the following contents: [" +
                                    ", ".join(f'"{o}"' for o in stored) + "]"]

    def answer(cmd):
        if cmd.startswith("data remove storage aoe2mc:orders"):
            got[0] = "Found no elements matching list"
        if cmd.startswith("data get storage aoe2mc:orders"):
            return got[0]
        if cmd.startswith("execute as "):
            return "Test passed, count: 1" if cmd.split()[2] in tagged else "Test failed"
        return command(cmd)
    server.command = answer
    scenario.orders(g)
    return server, g


def sent(server, uuid):
    return [c.split()[3:7] for c in server.log if c.startswith(f"aoe stats {uuid} ")]


def test_a_tagged_militia_gets_attack_plus_2_and_forging_adds_1():
    server, g = run("value aoe_order7_0 attack 2 2")
    base = combat.stats("MILITIA")
    assert sent(server, "m1")[-1][1] == str(base.attack + 2) and sent(server, "a1") == []
    assert "tag @e[tag=aoe_order7_0] remove aoe_order7_0" in server.log
    train.research(g, {"name": "FORGING", "player": "Steve"})
    assert sent(server, "m1")[-1][1] == str(base.attack + 3)
    assert train.stats(g, "MILITIA").attack == base.attack + 1          # the unit type has no trigger value


def test_armor_and_hit_points():
    base = combat.stats("MILITIA")
    server, g = run("value aoe_order7_0 melee 2 1", "value aoe_order7_1 pierce 1 5", "value aoe_order7_2 hp 2 10")
    assert sent(server, "m1")[-1] == [str(base.hp + 10), str(base.attack), str(base.melee + 1), "5"]
    server, g = run("value aoe_order7_0 hp 1 200")
    assert sent(server, "m1")[-1][0] == "200"
    train.research(g, {"name": "FORGING", "player": "Steve"})
    assert sent(server, "m1")[-1][0] == "200"                          # a technology keeps the hit points


def test_a_set_speed_stays_after_a_move_order():
    server, g = run("value aoe_order7_0 speed 1 2")
    T, attribute = g.map.T, ai.movement_speed("MILITIA", g.map.T, 2 / ai.walk_speed("MILITIA", 1, 1) * gather.NORMAL)
    assert f"attribute m1 minecraft:movement_speed base set {attribute}" in server.log
    assert attribute == round((2 * T * gather.NORMAL / ai.WALK) ** 0.5, 4)
    server.log.clear()
    ai.move(g, "m1", "MILITIA", T, 1, 2, 3, gather.NORMAL * train.speed(g, "MILITIA", "m1"))
    assert server.log[0] == f"attribute m1 minecraft:movement_speed base set {attribute}"
    assert train.speed(g, "MILITIA", "a1") == train.speed(g, "MILITIA")


def test_a_bot_unit_keeps_its_value_on_its_own_side():
    server, g, bot = game({"1": {}, "2": {}})
    bot.soldiers["b1"] = "MILITIA"
    command = server.command
    stored = ['Storage aoe2mc:orders has the following contents: ["value aoe_order7_0 attack 1 9"]']

    def answer(cmd):
        if cmd.startswith("data remove storage aoe2mc:orders"):
            stored[0] = "Found no elements matching list"
        if cmd.startswith("data get storage aoe2mc:orders"):
            return stored[0]
        if cmd.startswith("execute as "):
            return "Test passed, count: 1" if cmd.split()[2] == "b1" else "Test failed"
        return command(cmd)
    server.command = answer
    scenario.orders(g)
    assert sent(server, "b1")[-1][1] == "9" and bot.unit_values == {"b1": [["attack", 1, 9.0]]}
    assert "unit_values" not in vars(g)


@pytest.mark.mc
def test_the_trigger_lines_store_orders_that_the_game_program_reads_on_a_server(tmp_path):
    import json
    import os
    import re

    from test_paper import paper_reachable
    from game import run as game_run
    from tools import scenarios
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = str(tmp_path / "W")
    aoe2mc.convert(scenarios.tiny(str(tmp_path / "t.aoe2scenario")), world)
    t = trigger(aoe2mc.CHANGE_OBJECT_HP, aoe2mc.MODIFY_OBJECT_ATTRIBUTE_BY_VARIABLE)
    t["effects"][0].update(operation=2, quantity=10)
    t["effects"][1].update(attribute=9, armour_class=4, operation=3, variable=3)
    files = aoe2mc.trigger_files([t], 4, np.full((64, 64), 70, np.int16))[1]
    for path, text in files.items():
        dst = os.path.join(world, "datapacks", "aoe2mc", path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w") as f:
            f.write(text if isinstance(text, str) else json.dumps(text))
    with game_run.Game(world) as game:
        game.forceload()
        for cmd in ("scoreboard objectives add aoe_hp dummy", "scoreboard objectives add aoe_var dummy",
                    "scoreboard players set #v3 aoe_var 2"):
            game.command(cmd)
        for line in files["data/aoe2mc/function/trigger/7.mcfunction"].splitlines():
            out = game.command(line)
            assert not re.search("Unknown|Incorrect|Expected|Invalid", out), (line, out)
        got = game.command("data get storage aoe2mc:orders list")
    assert re.findall(scenario.ORDER_KINDS["values"], got) == [("aoe_order7_0", "hp", "2", "10"),
                                                               ("aoe_order7_1", "attack", "3", "2")]
