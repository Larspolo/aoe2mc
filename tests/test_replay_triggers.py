"""The live replay of a record with the triggers of a scenario (#5158): the replay clock runs the timer triggers, a unit
of "Create Object" appears once and the later commands of the record move it, the resources change the estimate."""
import os
import sys

import numpy as np
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.units import UnitInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import replay  # noqa: E402
from test_replay import data  # noqa: E402
from test_replay_control import Clock  # noqa: E402

import aoe2mc  # noqa: E402
from tools import scenarios  # noqa: E402

GROUND = np.full((64, 64), 70, np.int16)
PLAYERS = {1: {"color": "blue"}, 2: {"color": "red"}}


def triggers(tmp_path):
    """A scenario: the instructions at 10 s; at 20 s a Militia of player 1 and a tribute of 100 food to player 2."""
    scn = scenarios.new_scenario(16)
    t = scn.trigger_manager.add_trigger("Welcome")
    t.new_condition.timer(timer=10)
    t.new_effect.display_instructions(source_player=PlayerId.ONE, message="Hold the hill.", display_time=5)
    t = scn.trigger_manager.add_trigger("Militia")
    t.new_condition.timer(timer=20)
    t.new_effect.create_object(source_player=1, object_list_unit_id=UnitInfo.MILITIA.ID, location_x=3, location_y=5)
    t.new_effect.tribute(quantity=100, tribute_list=0, source_player=1, target_player=2)
    return aoe2mc.read_scenario(scenarios.save(scn, str(tmp_path / "t.aoe2scenario")))[4]["triggers"]


class Timed(Clock):
    """The fake clock and RCON, with the real time of each function command."""
    def command(self, cmd):
        if cmd.startswith("function "):
            self.at.setdefault(cmd, []).append(round(self.now, 3))
        return super().command(cmd)


def play(tmp_path, jump=None):
    trigs = triggers(tmp_path)
    welcome, militia = (t["id"] for t in trigs)
    d = data([{"time": 40000, "player": 1, "kind": "move", "objects": [50], "tile": [10.5, 2.5], "names": ["MILITIA"]}])
    d["timers"] = aoe2mc.timer_list(trigs, 4, GROUND, PLAYERS)
    game, done = Timed(), []

    def poll(control):
        if jump and game.now >= 1 and not done:
            control["jump"] = jump
            done.append(game.now)
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None, poll=poll, finish=True)
    return r, game, d, welcome, militia


def test_the_world_lists_the_timer_triggers_and_does_not_start_them(tmp_path):
    trigs = triggers(tmp_path)
    welcome, militia = (t["id"] for t in trigs)
    timers = aoe2mc.timer_list(trigs, 4, GROUND, PLAYERS)
    assert [(x["id"], x["time"]) for x in timers] == [(welcome, 10000), (militia, 20000)]
    unit, = timers[1]["units"]
    assert unit["name"] == "MILITIA" and unit["player"] == 1 and timers[1]["resources"] == [
        {"player": 2, "resource": "food", "add": 100}, {"player": 1, "resource": "food", "add": -100}]
    files = aoe2mc.trigger_files(trigs, 4, GROUND, PLAYERS, replay=True)[1]
    summon = files[f"data/aoe2mc/function/trigger/{militia}.mcfunction"]
    assert "UUID: [I; " in summon and "UUID" not in aoe2mc.trigger_files(trigs, 4, GROUND, PLAYERS)[1][
        f"data/aoe2mc/function/trigger/{militia}.mcfunction"]          # a scenario world: new UUIDs, as before
    for replayed, world in ((True, tmp_path / "R"), (False, tmp_path / "S")):
        aoe2mc.write_datapack(str(world), [], GROUND, players=PLAYERS, triggers=trigs, replay=replayed)
        with open(world / "datapacks" / "aoe2mc" / "data" / "aoe2mc" / "function" / "start.mcfunction") as f:
            assert (f"schedule function aoe2mc:trigger/{welcome} 200t replace" in f.read()) is not replayed


def test_the_record_names_the_unit_of_the_trigger():
    move = {"time": 40000, "player": 1, "kind": "move", "objects": [50], "tile": [10.5, 2.5]}
    assert aoe2mc.name_timeline([], [dict(move)], created=[(20000, "MILITIA", 1)])[50] == "MILITIA"
    assert 50 not in aoe2mc.name_timeline([], [dict(move)])


def test_the_replay_runs_the_triggers_at_their_times_and_moves_the_unit_once(tmp_path):
    r, game, d, welcome, militia = play(tmp_path)
    assert game.at[f"function aoe2mc:trigger/{welcome}"] == [10.0]
    assert game.at[f"function aoe2mc:trigger/{militia}"] == [20.0]
    uuid = d["timers"][1]["units"][0]["uuid"]
    assert not any(c.startswith("summon") for c in game.sent)           # the datapack function makes the unit
    assert r.units[50].uuid == uuid and any(c.startswith(f"tp {uuid} ") for c in game.sent)   # the record moves it
    assert r.resources(2)["food"] == replay.START["food"] + 100 and r.resources(1)["food"] == replay.START["food"] - 100


def test_a_jump_gives_the_state_of_the_triggers_at_its_time(tmp_path):
    r, game, d, welcome, militia = play(tmp_path, jump=30000)
    assert game.at[f"function aoe2mc:trigger/{welcome}"] == game.at[f"function aoe2mc:trigger/{militia}"] == [1.0]
    assert r.resources(2)["food"] == replay.START["food"] + 100
    assert r.units[50].uuid == d["timers"][1]["units"][0]["uuid"]


def test_a_looping_trigger_runs_again_after_its_timer(tmp_path):
    trig = dict(id=3, name="t", enabled=True, looping=True, conditions=[dict(type=aoe2mc.TIMER, timer=15, inverted=False)],
                effects=[dict(type=aoe2mc.DISPLAY_INSTRUCTIONS, message="Again.", player=1, time=4)])
    d = data([{"time": 50000, "player": 1, "kind": "chat", "text": "t50000"}])
    d["timers"] = timers = aoe2mc.timer_list([trig], 4, GROUND, PLAYERS)
    assert timers == [{"id": 3, "time": 15000, "every": 15000}]
    game = Timed()
    replay.Replay(game, d).run(clock=lambda: game.now, sleep=game.sleep, log=None)
    assert game.at["function aoe2mc:trigger/3"] == [15.0, 30.0, 45.0]
    assert game.sent.count("schedule clear aoe2mc:trigger/3") == 3     # the replay clock, not the server schedule
