"""#2576 (epic #2538): the trigger effects "Tribute" and "Modify Resource" change the scores #p<N>.<resource> of the
world (aoe2mc.resource_lines), and scenario.resources of `run.py --play --mode scenario` puts them into the stocks."""
import contextlib
import io
import os
import re
import sys

from AoE2ScenarioParser.datasets.trigger_lists import Operation
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario

import aoe2mc
from tools import scenarios

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402


def trig(*effects):
    return dict(id=7, name="t7", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)],
                effects=[dict(message="", time=-1, object=None, tile=[-1, -1], area=[-1] * 4) | e for e in effects])


def lines(*effects):
    load, files = aoe2mc.trigger_files([trig(*effects)])
    return load, files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_a_tribute_of_100_gold_moves_the_score_from_player_1_to_player_2():
    load, fn = lines(dict(type=aoe2mc.TRIBUTE, player=1, target=2, resource=3, quantity=100))
    assert fn == ["scoreboard players add #p2.gold aoe_res 100", "scoreboard players remove #p1.gold aoe_res 100"]
    assert load[:2] == ["scoreboard objectives add aoe_res dummy", "scoreboard objectives add aoe_set dummy"]


def test_modify_resource_sets_adds_and_subtracts():
    def one(op, q=250):
        return lines(dict(type=aoe2mc.MODIFY_RESOURCE, player=2, resource=0, operation=op, quantity=q))[1]
    assert one(Operation.SET) == ["scoreboard players set #p2.food aoe_set 250",
                                  "scoreboard players reset #p2.food aoe_res"]   # the earlier changes go
    assert one(Operation.ADD) == ["scoreboard players add #p2.food aoe_res 250"]
    assert one(Operation.SUBTRACT) == ["scoreboard players remove #p2.food aoe_res 250"]
    assert one(Operation.MULTIPLY) == []                                         # not yet


def test_gaia_and_unknown_resources_write_no_score():
    assert lines(dict(type=aoe2mc.TRIBUTE, player=0, target=2, resource=3, quantity=100)) == ([], [])
    assert lines(dict(type=aoe2mc.TRIBUTE, player=1, target=2, resource=9, quantity=100)) == ([], [])
    assert lines(dict(type=aoe2mc.TRIBUTE, player=1, target=0, resource=1, quantity=5))[1] == \
        ["scoreboard players remove #p1.wood aoe_res 5"]                         # a tribute to Gaia only costs


class Scores:
    """A fake RCON scoreboard on the fake server of test_gather: scoreboard players get and reset."""

    def __init__(self, server, values):
        self.values, command = values, server.command

        def score(cmd):
            if m := re.fullmatch(r"scoreboard players get (\S+) (\S+)", cmd):
                command(cmd)
                v = self.values.get((m[1], m[2]))
                return f"{m[1]} has {v} [{m[2]}]" if v is not None else f"Can't get value of {m[2]} for {m[1]}; none is set"
            if m := re.fullmatch(r"scoreboard players reset (\S+) (\S+)", cmd):
                self.values.pop((m[1], m[2]), None)
            return command(cmd)
        server.command = score


def test_resources_puts_the_tribute_into_the_stocks_and_resets_the_scores():
    server, g, bot = game({"1": {}, "2": {}})
    g.stock.update(gold=300)
    bot.stock.update(gold=50)
    scores = Scores(server, {("#p2.gold", "aoe_res"): 100, ("#p1.gold", "aoe_res"): -100})
    scenario.resources(g)
    assert g.stock["gold"] == 200 and bot.stock["gold"] == 150 and not scores.values
    assert f"scoreboard players set Gold {g.board} 200" in server.log
    n = len(server.log)
    scenario.resources(g)                                                   # once per EVERY seconds
    assert len(server.log) == n


def test_resources_sets_a_stock_and_never_below_0():
    server, g, bot = game({"1": {}, "2": {}})
    g.stock.update(food=300, wood=20)
    Scores(server, {("#p1.food", "aoe_set"): 1000, ("#p1.food", "aoe_res"): 50, ("#p1.wood", "aoe_res"): -100})
    scenario.resources(g)
    assert g.stock["food"] == 1050 and g.stock["wood"] == 0


def resource_scenario(path):
    """The tiny map with a timer trigger at 10 s: a tribute of 100 gold from player 1 to player 2."""
    with contextlib.redirect_stdout(io.StringIO()):
        scn = AoE2DEScenario.from_file(scenarios.tiny(str(path.with_suffix(".tiny"))))
    t = scn.trigger_manager.add_trigger("Gift")
    t.new_condition.timer(timer=10)
    t.new_effect.tribute(quantity=100, tribute_list=3, source_player=1, target_player=2)
    return scenarios.save(scn, str(path))


def test_the_effect_is_read_and_converted(tmp_path):
    src = resource_scenario(tmp_path / "r.aoe2scenario")
    (gift,) = aoe2mc.read_scenario(src)[4]["triggers"]
    e = gift["effects"][0]
    assert (e["player"], e["target"], e["resource"], e["quantity"]) == (1, 2, 3, 100)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    fn = os.path.join(tmp_path, "W", "datapacks", "aoe2mc", "data", "aoe2mc", "function")
    with open(os.path.join(fn, "trigger", f"{gift['id']}.mcfunction")) as f:
        assert "scoreboard players add #p2.gold aoe_res 100" in f.read().splitlines()
