"""Live replay of a recorded game (#374): the commands of each timeline event, with a fake RCON (no server)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402


class Fake:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return ""


def data(timeline, n=64, y=70):
    return {"map_size": n // 4, "tile_size": 4, "level_height": 3, "objects": [],
            "players": {"1": {"civ": "BRITONS", "color": "blue", "arch": "western"},
                        "2": {"civ": "AZTECS", "color": "orange", "arch": "meso"}},
            "ground": [" ".join([str(y)] * n)] * n, "timeline": timeline}


def build(name="HOUSE", tile=(8.0, 8.0), t=1000, player=1):
    types = {"HOUSE": 70, "PALISADE_WALL": 72}
    return {"time": t, "player": player, "kind": "build", "type": types[name], "name": name, "tile": list(tile)}


def test_chat_age_research_resign():
    r = replay.Replay(Fake(), data([]))
    chat = r.commands({"time": 0, "player": 2, "kind": "chat", "text": 'gl "hf"'})
    assert len(chat) == 1 and chat[0].startswith("tellraw @a ")
    assert json.loads(chat[0][len("tellraw @a "):]) == [{"text": "<Player 2 (Aztecs)> ", "color": "gold"},
                                                        {"text": 'gl "hf"'}]
    age = r.commands({"time": 1, "player": 1, "kind": "age", "age": "FEUDAL_AGE"})
    assert age[-1] == 'title @a title {"text": "Feudal Age"}' and '"color": "blue"' in age[0]
    tech = r.commands({"time": 2, "player": 1, "kind": "research", "technology": "Loom"})
    assert tech[0].startswith("title @a actionbar ") and "researches Loom" in tech[0]
    end = r.commands({"time": 3, "player": 1, "kind": "resign"})
    assert end[-1].startswith("title @a title ") and "Player 1 (Britons) resigns" in end[-1]
    assert r.commands({"time": 4, "player": 1, "kind": "move", "tile": [3.0, 4.0]}) == []


def test_building_on_the_ground():
    r = replay.Replay(Fake(), data([]))
    cmds = r.commands(build())
    assert cmds[0] == "fill 28 70 28 35 " + cmds[0].split()[5] + " 35 air"    # the footprint of a house: 2 tiles
    ys = [int(c.split()[2]) for c in cmds[1:]]
    assert min(ys) == 69 and ys == sorted(ys)                     # from the bottom up: the floor replaces the grass
    for c in cmds[1:]:
        x, z = int(c.split()[1]), int(c.split()[3])
        assert 24 <= x < 40 and 24 <= z < 40
    assert any(c.split()[-1].startswith("minecraft:") and c.split()[0] == "fill" for c in cmds)
    assert r.commands(build(t=2000)) == []                                    # a second click on the foundation


def test_building_on_a_slope_gets_a_foundation():
    d = data([])
    d["ground"] = [" ".join(str(70 + 2 * (x >= 32)) for x in range(64)) for _ in range(64)]
    cmds = replay.Replay(Fake(), d).commands(build())
    assert cmds[0].startswith("fill 28 72 28 35 ")                             # the floor on the highest cell
    assert cmds[1].startswith("fill 28 70 28 35 70 35 ") and cmds[1].endswith(" keep")


def test_building_on_water_or_outside_is_skipped():
    d = data([])
    d["ground"] = [" ".join(["-"] * 64)] * 64
    assert replay.Replay(Fake(), d).commands(build()) == []
    assert replay.Replay(Fake(), data([])).commands(build(tile=(200.0, 200.0))) == []


def test_wall_gives_one_piece_per_tile():
    r = replay.Replay(Fake(), data([]))
    e = dict(build("PALISADE_WALL"), kind="wall", tile=[4.0, 8.0], end=[6, 8])
    cmds = r.commands(e)
    assert sum(c.endswith(" air") for c in cmds) == 3


def test_run_plays_in_time_and_counts():
    timeline = [{"time": 0, "player": 1, "kind": "chat", "text": "hi"}, build(t=8000),
                {"time": 12000, "player": 1, "kind": "resign"}]
    now, waits = [0.0], []

    def sleep(s):
        waits.append(round(s, 3))
        now[0] += s
    game = Fake()
    stats = replay.Replay(game, data(timeline)).run(speed=4, clock=lambda: now[0], sleep=sleep, log=None)
    assert waits == [2.0, 1.0]                                                 # 8 s and 12 s of game time at speed 4
    assert stats["events"] == 3 and stats["commands"] == len(game.sent) and stats["lag"] == 0
    assert any(c.startswith("tellraw") for c in game.sent) and game.sent[-1].startswith("title @a title")  # the army
    # texts (#3696) are summoned before the first chat line
    later = replay.Replay(Fake(), data(timeline)).run(speed=4, start=10000, clock=lambda: now[0], sleep=sleep,
                                                       log=None)
    assert later["events"] == 1
