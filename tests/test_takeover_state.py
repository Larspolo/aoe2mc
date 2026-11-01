"""The state of a live replay at its time is a game save (#5449): savegame.load puts it on the Gather of a test game,
which then has the stock, technologies, units and buildings of the replay and its game time."""
import json
import os

import gather
import replay
import run
import savegame
import takeover
from test_gather import FakeServer
from test_replay import build, data
from test_replay_control import Clock
from test_replay_gather import TREE, VIL, order

SOLDIER = {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m1", "ref": 8, "tile": [4.5, 12.5]}
OTHER = {"kind": "unit", "name": "VILLAGER_FEMALE", "player": 2, "uuid": "u2", "ref": 9, "tile": [12.5, 12.5]}


def played():
    """A replay after an order, a house, an age-up and a research of player 1."""
    d = data([order(0, 20), build("HOUSE", (3.0, 3.0), 500), dict(time=600, player=1, kind="age", age="FEUDAL_AGE"),
              dict(time=700, player=1, kind="research", technology="Loom")])
    d["objects"] += [VIL, TREE, SOLDIER, OTHER]
    r = replay.Replay(Clock(), d)
    for e in d["timeline"]:
        r.commands(e)
    return r, d


def test_a_load_gives_the_state_of_the_replay():
    r, d = played()
    text = json.dumps(takeover.state(r, 750), sort_keys=True)
    server = FakeServer({u: {"Pos": (o["tile"][0] * 4, 70.0, o["tile"][1] * 4)} for o in d["objects"]
                         if (u := o.get("uuid"))})
    g = gather.Gather(server, json.loads(json.dumps(d)), start={}).setup()
    savegame.load(g, json.loads(text))
    stock = r.stock[1]
    assert g.stock == {k: max(0, int(v)) for k, v in stock.items()} and any(v < 0 for v in stock.values())
    assert g.techs == {"FEUDAL_AGE", "LOOM"} and g.pop == r.pop[1]
    assert g.soldiers == {"m1": "MILITIA"} and [u["uuid"] for u in g.units] == ["u1"]
    assert set(g.villagers) == {"u1"} and g.villagers["u1"].pos == r.units[7].pos
    site, = g.sites
    assert (site["name"], site["footprint"], site["done"]) == ("HOUSE", r.placed[0][2], True)
    assert g.game.loaded_seconds == 0.75


def test_each_player_has_its_own_units():
    r, _ = played()
    d = takeover.state(r, 0)
    two = d["players"]["2"]
    assert sorted(d["players"]) == ["1", "2"] and two["techs"] == [] and not savegame.unpack(two["sites"])
    assert [u["uuid"] for u in savegame.unpack(two["units"])] == ["u2"] and savegame.unpack(two["soldiers"]) == {}


def test_the_same_replay_at_the_same_time_gives_the_same_dict():
    a, b = (json.dumps(takeover.state(played()[0], 750)) for _ in range(2))
    assert a == b and a == json.dumps(json.loads(a), sort_keys=True)


def test_write_puts_the_world_and_the_state_into_a_save(tmp_path, monkeypatch):
    r, _ = played()
    world = tmp_path / "MyWorld"
    world.mkdir()
    (world / "level.dat").write_bytes(b"x")
    game = type("Game", (), {"world": str(world)})()
    copies = tmp_path / "copies"

    def save(game):
        folder = copies / "tmp1"
        folder.mkdir(parents=True)
        (folder / "level.dat").write_bytes(b"x")
        return str(folder)
    monkeypatch.setattr(run, "save", save)
    path = takeover.write(game, r, str(tmp_path / "saves"), 750)
    assert os.path.basename(path).startswith("MyWorld-") and os.path.isfile(os.path.join(path, "world", "level.dat"))
    assert savegame.read(path) == json.loads(json.dumps(takeover.state(r, 750)))
    assert os.listdir(copies) == []                                    # the copy of the server is gone
