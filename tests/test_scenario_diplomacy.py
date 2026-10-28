"""#2645 (epic #2538): a scenario trigger with the effect "Change Diplomacy" changes the stance of one player to another
in the scenario mode. The converter sets the score #p<N>.p<M> of aoe_dip, and scenario.diplomacy reads it."""
import os
import sys
import types
from collections import Counter

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import scenario  # noqa: E402


def change(a=1, b=2, stance=3):
    e = dict(type=aoe2mc.CHANGE_DIPLOMACY, message="", player=a, target=b, diplomacy=stance, time=0, object=None,
             tile=[-1, -1], area=[-1, -1, -1, -1])
    return dict(id=5, name="War", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=60, inverted=False)], effects=[e])


def test_the_trigger_function_sets_the_score_of_the_stance():
    stats = Counter()
    load, files = aoe2mc.trigger_files([change()], 4, np.full((16, 16), 64, np.int16), {}, stats)
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines() == [
        "scoreboard players set #p1.p2 aoe_dip 4", "scoreboard players set #any aoe_dip 1"]
    assert load[0] == "scoreboard objectives add aoe_dip dummy"
    assert stats == Counter({"change diplomacy": 1})


def test_a_change_to_gaia_or_itself_makes_no_function():
    load, files = aoe2mc.trigger_files([change(1, 0), change(2, 2)], 4, np.full((16, 16), 64, np.int16), {})
    assert not files and "scoreboard objectives add aoe_dip dummy" not in load


class Game:
    def __init__(self, players, scores, treaty=0.0):
        self.players, self.scores, self.log = players, scores, []
        self.game = types.SimpleNamespace(treaty=treaty, treaty_time=0.0)

    def command(self, cmd):
        self.log.append(cmd)
        w = cmd.split()
        if w[:3] == ["scoreboard", "players", "get"]:
            return f"{w[3]} has {self.scores[w[3]]} [aoe_dip]" if w[3] in self.scores else \
                f"Can't get value of aoe_dip for {w[3]}; none is set"
        if w[:3] == ["scoreboard", "players", "reset"]:
            self.scores.pop(w[3], None)
        return ""


def test_enemy_ends_the_alliance_and_resets_the_score():
    g = Game({"0": {}, "1": {"team": 1}, "2": {"team": 1}}, {"#any": 1, "#p1.p2": 4})
    scenario.diplomacy(g)
    assert not gather.allied(g.players, 1, 2)
    assert g.scores == {}
    assert g.log[-2:] == ["aoe allies -", "aoe neutral -"]


def test_neutral_and_ally():
    g = Game({"0": {}, "1": {}, "2": {}, "3": {"team": 2}}, {"#any": 1, "#p1.p2": 2, "#p2.p3": 1})
    scenario.diplomacy(g)
    assert g.players["1"] == {"neutral": [2]} and gather.allied(g.players, 2, 3)
    assert g.log[-2:] == ["aoe allies p2,p3", "aoe neutral p1:p2"]


def test_no_change_reads_one_score():
    g = Game({"0": {}, "1": {}, "2": {}}, {})
    scenario.diplomacy(g)
    assert g.log == ["scoreboard players get #any aoe_dip"]


def test_a_treaty_keeps_the_neutral_stances():
    g = Game({"0": {}, "1": {"neutral": [2]}, "2": {}}, {"#any": 1, "#p1.p2": 4}, treaty=600.0)
    scenario.diplomacy(g)
    assert g.players["1"] == {} and not any(c.startswith("aoe neutral") for c in g.log)
