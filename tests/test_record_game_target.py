"""Record Game (#3004): an attack on a building takes the ID of that building, with its middle tile."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import combat  # noqa: E402
import record  # noqa: E402
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402

MILITIA = {"kind": "unit", "name": "MILITIA", "player": 1, "ref": 7, "uuid": "u-militia", "tile": [10.0, 10.0]}
CASTLE = {"kind": "building", "name": "CASTLE", "player": 2, "ref": 1, "footprint": [40, 8, 56, 24], "tile": [12.0, 4.0]}
CASTLE_UUID = combat.target_uuid([40, 8, 56, 24])                    # the UUID that Gather.attack sends


def world():
    d = data([])
    del d["timeline"]                                                  # a converted scenario has no timeline
    d["objects"] += [MILITIA, CASTLE]
    return d


def game(tmp_path, name="game.jsonl"):
    g = types.SimpleNamespace(data=world(), player=1, map=types.SimpleNamespace(T=4))
    path = str(tmp_path / name)
    record.start([g], path)
    return g, path


def test_an_attack_on_a_start_building_takes_its_id(tmp_path):
    g, path = game(tmp_path)
    record.ordered(g, "order", {"u-militia"}, target=CASTLE_UUID)
    g.record.f.close()
    refs, timeline = record.load(path)
    assert refs == {"u-militia": 7, "40,56,8,24": 1}                   # no new ID for the castle
    assert timeline == [{"time": 0, "player": 1, "kind": "order", "objects": [7], "target": 1, "tile": [12.0, 4.0]}]


def test_an_attack_on_a_foundation_takes_the_id_of_the_foundation(tmp_path):
    g, path = game(tmp_path)
    record.built(g, "HOUSE", (28, 36, 28, 36))                         # footprint [28, 28, 36, 36]
    record.ordered(g, "order", {"u-militia"}, target=combat.target_uuid([28, 28, 36, 36]))
    g.record.f.close()
    refs, timeline = record.load(path)
    assert refs["28,36,28,36"] == 8 and timeline[-1]["target"] == 8
    assert len([line for line in open(path) if "refs" in line]) == 2   # the start line and the house, no castle


def test_a_villager_after_an_attack_on_a_building_keeps_its_name(tmp_path):
    g, path = game(tmp_path)
    record.queued(g, "VILLAGER_MALE", (40, 56, 8, 24))                 # the castle queues a villager at 0 s
    record.tick(g, 24)
    record.ordered(g, "order", {"u-militia"}, target=CASTLE_UUID)     # the attack at 24 s
    record.tick(g, 1)
    record.trained(g, "u-villager")                                    # the villager comes at 25 s
    record.tick(g, 15)
    record.ordered(g, "move", {"u-villager"}, cell=(40, 44))           # its move at 40 s
    g.record.f.close()
    d = record.apply(world(), path)
    move = next(e for e in d["timeline"] if e["kind"] == "move")
    assert move["names"] == ["VILLAGER_MALE"]


def test_the_replay_attacks_the_castle_with_its_uuid(tmp_path):
    g, path = game(tmp_path)
    record.ordered(g, "order", {"u-militia"}, target=CASTLE_UUID)
    g.record.f.close()
    r = replay.Replay(Fake(), record.apply(world(), path), ai=True)
    cmds = r.commands(r.data["timeline"][0])
    assert any(c.startswith(f"aoe attack u-militia {CASTLE_UUID}") for c in cmds)
