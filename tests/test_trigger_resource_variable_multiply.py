"""#2941 (epic #2538): "Modify Resource by Variable" with multiply or divide sets the resource to the stock of the game
program (with the pending change) times or divided by the score #v<N> of aoe_var (aoe2mc.resource_by_variable_lines)."""
import os
import re
import sys

from AoE2ScenarioParser.datasets.trigger_lists import Operation

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_scenario_resources import Scores, lines  # noqa: E402


def effect(op, player=1, resource=0, variable=2):
    return lines(dict(type=aoe2mc.MODIFY_RESOURCE_BY_VARIABLE, player=player, resource=resource, operation=op,
                      variable=variable))


def run(fn, scores):
    """The function lines on a dict of scores {(holder, objective): value}: set, operation, reset, execute if score."""
    for line in fn:
        if m := re.fullmatch(r"execute if score (\S+) (\S+) matches -2147483648\.\. run (.*)", line):
            if (m[1], m[2]) not in scores:
                continue
            line = m[3]
        w = line.split()
        if w[:3] == ["scoreboard", "players", "set"]:
            scores[w[3], w[4]] = int(w[5])
        elif w[:3] == ["scoreboard", "players", "reset"]:
            scores.pop((w[3], w[4]), None)
        elif w[:3] == ["scoreboard", "players", "operation"]:
            a, b = scores.get((w[3], w[4]), 0), scores.get((w[6], w[7]), 0)
            if w[5] == "/=" and b == 0:                                # Minecraft keeps the score
                continue
            scores[w[3], w[4]] = {"=": b, "+=": a + b, "*=": a * b, "/=": a // b if b else a}[w[5]]
        else:
            raise AssertionError(line)
    return scores


def test_multiply_of_food_by_variable_2_finds_the_operation_line():
    load, fn = effect(Operation.MULTIPLY)
    assert "scoreboard players operation #res aoe_var *= #v2 aoe_var" in fn
    assert fn[-2:] == ["scoreboard players operation #p1.food aoe_set = #res aoe_var",
                       "scoreboard players reset #p1.food aoe_res"]
    assert "scoreboard objectives add aoe_var dummy" in load
    assert "scoreboard players operation #res aoe_var /= #v2 aoe_var" in effect(Operation.DIVIDE)[1]


def test_player_2_reads_its_own_board():
    fn = effect(Operation.MULTIPLY, player=2)[1]
    assert "execute if score Food aoe_res2 matches -2147483648.. run scoreboard players operation #res aoe_var = " \
           "Food aoe_res2" in fn


def test_food_100_times_3_gives_player_1_300_food():
    server, g, bot = game({"1": {}, "2": {}})
    g.stock.update(food=100)
    scores = run(effect(Operation.MULTIPLY)[1], {("Food", "aoe_res"): 100, ("#v2", "aoe_var"): 3})
    Scores(server, {k: v for k, v in scores.items() if k[0] == "#p1.food"})
    scenario.resources(g)
    assert g.stock["food"] == 300 and f"scoreboard players set Food {g.board} 300" in server.log


def test_the_pending_change_and_set_count_before_the_multiply():
    scores = {("Food", "aoe_res"): 100, ("#v2", "aoe_var"): 3, ("#p1.food", "aoe_res"): 20}
    assert run(effect(Operation.MULTIPLY)[1], dict(scores))["#p1.food", "aoe_set"] == 360
    scores["#p1.food", "aoe_set"] = 50
    assert run(effect(Operation.DIVIDE)[1], scores)["#p1.food", "aoe_set"] == 16


def test_a_division_by_0_keeps_the_stock():
    scores = run(effect(Operation.DIVIDE)[1], {("Food", "aoe_res"): 100, ("#v2", "aoe_var"): 0})
    assert scores["#p1.food", "aoe_set"] == 100
