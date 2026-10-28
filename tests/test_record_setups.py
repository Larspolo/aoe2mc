"""Record Game (#3028): the objects that the setups of run.play make before the game starts (the scout of a
civilization, the start buildings, the town and units of a game mode) are in the record at 0:00, so the replay has them."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import build  # noqa: E402
import gather  # noqa: E402
import record  # noqa: E402
import replay  # noqa: E402
import run  # noqa: E402
import scout  # noqa: E402
import train  # noqa: E402
from test_gather import FakeServer  # noqa: E402
from test_replay import Fake, data  # noqa: E402

TC = {"kind": "building", "name": "TOWN_CENTER", "player": 1, "ref": 1, "tile": [4.0, 4.0], "footprint": [8, 8, 24, 24]}
SCOUT = {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "ref": 2, "uuid": "old-scout", "tile": [10.0, 10.0]}


def world():
    """The converted start world: an Aztec player 1 with a town center and a Scout Cavalry."""
    d = data([])
    del d["timeline"]                                                  # a converted scenario has no timeline
    d["players"]["1"]["civ"] = "AZTECS"
    d["objects"] += [TC, SCOUT]
    return d


def game(tmp_path):
    """A Gather of player 1 that records into a file, as run.play starts it before the setups."""
    g = gather.Gather(FakeServer({"old-scout": {"Pos": (40.0, 70.0, 40.0)}}), world()).setup()
    path = str(tmp_path / "game.jsonl")
    record.start([g], path)
    return g, path


def play(g, path, uuid, at=5):
    """The game starts; at `at` s the unit uuid moves. Returns the replay of the record and the commands of each event."""
    record.play([g])
    record.tick(g, at)
    record.ordered(g, "move", {uuid}, cell=(40, 44))
    g.record.f.close()
    r = replay.Replay(Fake(), record.apply(world(), path), ai=True)
    return r, [(e, r.commands(e)) for e in r.data["timeline"]]


def test_the_scout_of_the_civilization_obeys_its_move_in_the_replay(tmp_path):
    g, path = game(tmp_path)
    scout.swap(g)
    eagle, = [u for u, n in g.soldiers.items() if n == "EAGLE_SCOUT"]
    r, events = play(g, path, eagle)
    move = next(c for e, c in events if e["kind"] == "move")
    assert next(e for e, _ in events if e["kind"] == "move")["names"] == ["EAGLE_SCOUT"]
    new, = [v for v in r.units.values() if v.player == 1]
    assert new.name == "EAGLE_SCOUT" and any(c.startswith(f"aoe moveto {new.uuid} ") for c in move)
    assert [(e["kind"], e["time"]) for e, _ in events] == [("delete", 0), ("summon", 0), ("move", 5000)]
    assert "kill old-scout" in events[0][1] and r.lost.get(1, 0) == 0   # no loss: a swap
    assert r.pop[1] == 1                                               # the Eagle Scout, not two scouts


def test_a_free_foundation_of_a_setup_is_in_the_replay_at_the_start_and_costs_nothing(tmp_path):
    g, path = game(tmp_path)
    build.found(g, "HOUSE", (28, 36, 28, 36), free=True)               # as start_buildings.place, empire_wars.town
    r, events = play(g, path, "old-scout")
    (house, cmds), _ = events
    assert (house["kind"], house["time"], house["name"], house["free"]) == ("build", 0, "HOUSE", True)
    assert any(c.startswith("fill 28 ") for c in cmds)                 # the house stands
    assert r.resources(1) == replay.START                              # no cost


def test_a_villager_of_a_setup_obeys_its_move_in_the_replay(tmp_path):
    g, path = game(tmp_path)
    v = train.spawn(g, (8, 24, 8, 24), "VILLAGER_MALE")                # as empire_wars.setup
    r, events = play(g, path, v.uuid)
    (summon, cmds), (move, walk) = events
    assert summon["kind"] == "summon" and summon["names"] == ["VILLAGER_MALE"] == move["names"]
    new = r.units[summon["objects"][0]]
    assert cmds[0].startswith("summon ") and any(c.startswith(f"aoe moveto {new.uuid} ") for c in walk)
    assert r.resources(1) == replay.START


def test_a_unit_of_the_game_is_no_setup(tmp_path):
    g, path = game(tmp_path)
    record.play([g])
    train.summon(g, "MILITIA", (40.5, 70.0, 40.5))                     # a cheat or a queue: no summon event
    g.record.f.close()
    assert record.load(path)[1] == []


def test_play_starts_the_record_before_the_setups(tmp_path, monkeypatch):
    (tmp_path / "aoe2mc.json").write_text('{"players": {"1": {"civ": "AZTECS"}}, "tile_size": 4}')
    seen = []

    class FakeGather:
        bots, villagers, units, ended, speed, data = (), [], [], None, 1.0, {"objects": []}

        def __init__(self, *a, **k):
            pass

        def setup(self):
            pass

        def run(self, seconds):
            seen.append(("run", self.record.setup))
    monkeypatch.setattr(gather, "Gather", FakeGather)
    monkeypatch.setattr(scout, "swap", lambda g: seen.append(("swap", g.record.setup)))
    import combat
    monkeypatch.setattr(combat, "setup", lambda game, data: None)
    from test_play_speed import FakeGame
    run.play(FakeGame(), str(tmp_path), record=str(tmp_path / "game.jsonl"))
    assert seen == [("swap", True), ("run", False)]
