"""#2774 (epic #2538): a scenario trigger with the effect "Set Player Visibility" shows the units of one player to
another out of sight in the scenario mode, or hides them again. The converter sets the score #p<N>.p<M> of aoe_vis,
scenario.visibility reads it, and fog.update does not hide the units of a seen player."""
import os
import sys
import types
from collections import Counter

import numpy as np

import aoe2mc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import fog  # noqa: E402
import scenario  # noqa: E402


def trigger(a=1, b=2, state=0):
    e = dict(type=aoe2mc.SET_PLAYER_VISIBILITY, message="", player=a, target=b, visibility=state, time=0,
             object=None, tile=[-1, -1], area=[-1, -1, -1, -1])
    return dict(id=5, name="Spy", enabled=True, looping=False,
                conditions=[dict(type=aoe2mc.TIMER, timer=60, inverted=False)], effects=[e])


def test_the_trigger_function_sets_the_score_of_the_state():
    stats = Counter()
    load, files = aoe2mc.trigger_files([trigger()], 4, np.full((16, 16), 64, np.int16), {}, stats)
    assert files["data/aoe2mc/function/trigger/5.mcfunction"].splitlines() == [
        "scoreboard players set #p1.p2 aoe_vis 1", "scoreboard players set #any aoe_vis 1"]
    assert "scoreboard objectives add aoe_vis dummy" in load
    assert stats == Counter({"set player visibility": 1})


def test_gaia_or_itself_makes_no_function():
    load, files = aoe2mc.trigger_files([trigger(1, 0), trigger(2, 2)], 4, np.full((16, 16), 64, np.int16), {})
    assert not files and "scoreboard objectives add aoe_vis dummy" not in load


class Game:
    """A Gather of player 1 with one enemy unit of player 2 far out of sight."""
    def __init__(self, scores):
        self.player, self.scores, self.log = 1, scores, []
        self.players = {"0": {}, "1": {}, "2": {}}
        self.data = {"objects": [{"kind": "unit", "player": 2, "uuid": "e1", "name": "KNIGHT"}]}
        self.enemies, self.villagers, self.soldiers = {"e1": "KNIGHT"}, {}, {}
        self.bots, self.peers = [], []
        self.map = types.SimpleNamespace(T=4)

    def command(self, cmd):
        self.log.append(cmd)
        w = cmd.split()
        if w[:3] == ["scoreboard", "players", "get"]:
            return f"{w[3]} has {self.scores[w[3]]} [aoe_vis]" if w[3] in self.scores else "none is set"
        if w[:3] == ["scoreboard", "players", "reset"]:
            self.scores.pop(w[3], None)
        return ""

    def seen_tiles(self, pos, uuids):
        return set()


def hidden(g, monkeypatch):
    monkeypatch.setattr(fog, "revealed", lambda g, start=False: set())
    monkeypatch.setattr(fog, "targets", lambda g: set())
    fog.update(g, {"e1": (400.0, 64.0, 400.0)})
    return g.fog["hidden"]


def test_visible_shows_the_units_and_invisible_hides_them_again(monkeypatch):
    g = Game({"#any": 1, "#p1.p2": 1})
    scenario.visibility(g)
    assert g.players["1"] == {"sees": [2]} and g.scores == {}
    assert hidden(g, monkeypatch) == set()
    g.scores = {"#any": 1, "#p1.p2": 3}
    scenario.visibility(g)
    assert g.players["1"] == {}
    assert hidden(g, monkeypatch) == {"e1"}


def test_no_change_reads_one_score():
    g = Game({})
    scenario.visibility(g)
    assert g.log == ["scoreboard players get #any aoe_vis"]
