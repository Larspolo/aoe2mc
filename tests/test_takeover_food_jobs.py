"""A takeover keeps the food jobs of the villagers (#5699): the carcass of a hunted sheep is in the map of the replay
only (Replay.map.carcasses), so the save of a takeover must keep the amounts of the map, else the hunter stops."""
import json

import gather
import replay
import savegame
import takeover
from test_gather import FakeServer
from test_replay import data
from test_replay_control import Clock
from test_replay_gather import VIL, order
from test_replay_jump_team import SHEEP

END = 40000                                                            # the sheep has food left at this time


def hunted():
    """A replay that plays to END: villager u1 hunts the sheep from time 0 on."""
    d = data([dict(order(0, 30), tile=[5.5, 10.5]), dict(time=END, player=1, kind="chat", text="end")])
    d["objects"] += [VIL, SHEEP]
    game = Clock()
    r = replay.Replay(game, d)
    r.run(clock=lambda: game.now, sleep=game.sleep, log=None)
    return r


def loaded(r, t):
    """The Gather of a test game after savegame.load of the takeover of r at time t."""
    d = json.loads(json.dumps(takeover.state(r, t)))
    v = r.units[7]
    server = FakeServer({"u1": {"Pos": v.pos}})
    g = gather.Gather(server, json.loads(json.dumps(r.data)), start={}).setup()
    savegame.load(g, d)
    return g


def test_a_hunter_gathers_food_after_a_takeover():
    r = hunted()
    tile = r.hunted[30]
    assert r.units[7].tree == tile and r.units[7].res == "food"
    g = loaded(r, END)
    v = g.villagers["u1"]
    assert v.tree == tile and g.map.carcasses.get(tile, 0) > 0
    for _ in range(40):
        g.step()
    assert v.state != "idle" and v.load > 0
