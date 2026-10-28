"""#2968: the trigger effects "Tribute" and "Research Technology" each check once per second with their own timer. Before,
scenario.research and scenario.resources shared the key scenario_at, so resources never ran in a game (Gather.run calls
research first, in scenario.tick). This test runs the three calls in the order of Gather.run with a fake clock."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_scenario_resources import Scores  # noqa: E402


def run_steps(g, seconds):
    """Gather.run order: scenario.victory, scenario.tick, scenario.resources, every 0.25 s of the fake clock."""
    now = [0.0]
    g.clock = lambda: now[0]
    for _ in range(int(seconds / 0.25)):
        now[0] += 0.25
        scenario.victory(g)
        scenario.tick(g)
        scenario.resources(g)


def test_a_tribute_reaches_the_stock_in_the_gather_run_order():
    server, g, _ = game({"0": {}, "1": {}, "2": {}})
    g.stock.update(gold=300)
    scores = Scores(server, {("#p1.gold", "aoe_res"): 100})
    run_steps(g, 10)
    assert g.stock["gold"] == 400 and not scores.values


def test_a_research_and_a_tribute_both_work_in_the_gather_run_order():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    g.stock.update(gold=300)
    g.data["research"] = [dict(score="#r3.1", player=2, technology="LOOM")]
    scores = Scores(server, {("#p1.gold", "aoe_res"): 100, ("#r3.1", "aoe_tech"): 1})
    run_steps(g, 10)
    assert "LOOM" in bot.techs and g.stock["gold"] == 400 and ("#p1.gold", "aoe_res") not in scores.values
