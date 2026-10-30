"""#2577 (epic #2538): the trigger effect "Research Technology" gives its technology in the scenario mode. The converter
sets a score in aoe_tech and lists the effect in aoe2mc.json "research"; scenario.tick gives the technology."""
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import scenario  # noqa: E402
import train  # noqa: E402
from test_scenario_mode import game  # noqa: E402
from test_trigger_objects import effect, trig  # noqa: E402

import aoe2mc  # noqa: E402


def research(tech, player=1):
    return dict(effect(aoe2mc.RESEARCH_TECHNOLOGY, player=player), technology=tech)


def test_the_effect_sets_a_score_for_the_game_program():
    stats = Counter()
    load, files = aoe2mc.trigger_files([trig([research("LOOM")])], stats=stats)
    assert "scoreboard players set #r7.0 aoe_tech 1" in files["data/aoe2mc/function/trigger/7.mcfunction"]
    assert "scoreboard objectives add aoe_tech dummy" in load and stats == Counter(research=1)
    assert aoe2mc.research_list([trig([research("LOOM")])]) == [dict(score="#r7.0", player=1, technology="LOOM")]
    assert aoe2mc.research_list([trig([research("LOOM", player=0)])]) == []   # Gaia has no technologies


class Scores:
    """The server with the aoe_tech scores of the fired triggers (RCON scoreboard players get and set)."""

    def __init__(self, server, scores):
        self.server, self.scores = server, scores
        command = server.command

        def answer(cmd):
            parts = cmd.split()
            if parts[:3] == ["scoreboard", "players", "get"] and parts[4] == "aoe_tech":
                return f"{parts[3]} has {self.scores.get(parts[3], 0)} [aoe_tech]"
            if parts[:3] == ["scoreboard", "players", "set"] and parts[4] == "aoe_tech":
                self.scores[parts[3]] = int(parts[5])
            return command(cmd)
        server.command = answer


def test_tick_gives_the_technology_as_a_research_at_the_town_center():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    _, ref, _ = game({"0": {}, "1": {}, "2": {}})
    g.data["research"] = [dict(score="#r7.0", player=1, technology="LOOM")]
    scores = Scores(server, {"#r7.0": 1}).scores
    hp = train.stats(g, "VILLAGER_MALE").hp
    scenario.tick(g)
    train.research(ref, {"name": "LOOM", "player": "@a"})
    assert "LOOM" in g.techs and "LOOM" not in bot.techs and scores["#r7.0"] == 0
    assert train.stats(g, "VILLAGER_MALE") == train.stats(ref, "VILLAGER_MALE") and train.stats(g, "VILLAGER_MALE").hp > hp


def test_tick_gives_a_technology_to_a_bot_and_waits_for_the_trigger():
    server, g, bot = game({"0": {}, "1": {}, "2": {}})
    g.data["research"] = [dict(score="#r3.1", player=2, technology="LOOM")]
    scores = Scores(server, {}).scores
    scenario.tick(g)
    assert "LOOM" not in bot.techs
    scores["#r3.1"], g.research_at = 1, 0.0
    scenario.tick(g)
    assert "LOOM" in bot.techs and "LOOM" not in g.techs


def test_an_unknown_technology_gives_no_error(capsys):
    server, g, _ = game({"0": {}, "1": {}})
    g.data["research"] = [dict(score="#r7.0", player=1, technology="NO_SUCH_TECH")]
    Scores(server, {"#r7.0": 1})
    before = set(g.techs)
    scenario.tick(g)
    assert g.techs == before and "no NO_SUCH_TECH" in capsys.readouterr().err
