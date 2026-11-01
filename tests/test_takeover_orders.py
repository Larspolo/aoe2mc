"""A takeover keeps the orders of the replay (#5453): the gatherers, the builders, the stances, the garrisons and the
queues of the record become the orders of the save, and savegame.load gives them to the Gather."""
import json

import gather
import savegame
import takeover
from test_gather import FakeServer
from test_replay_garrison import RECT, TREE, order, play, vil

MIL = {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m1", "ref": 10, "tile": [12.5, 2.5]}
END = 6000


def played():
    """A replay with a gatherer (7), a builder (11), a garrisoned unit (8), a defensive militia and a queued villager."""
    timeline = [order(0, [7], 20), order(0, [8], 50, "garrison"),
                dict(time=0, player=1, kind="stance", objects=[10], stance="Defensive"),
                dict(time=0, player=1, kind="build", type=70, name="HOUSE", tile=[12.0, 12.0], objects=[11],
                     names=["VILLAGER_MALE"]),
                dict(time=END - 1000, player=1, kind="queue", objects=[50], type=83, name="VILLAGER_MALE", amount=1)]
    extra = [TREE, MIL, vil(11, "u3", [10.5, 10.5]), vil(12, "u4", [14.5, 2.5])]
    r, _ = play(timeline, END, ai=True, extra=extra)
    return r, extra


def loaded(r, extra):
    d = r.data
    server = FakeServer({u: {"Pos": (o["tile"][0] * 4, 70.0, o["tile"][1] * 4)} for o in d["objects"]
                         if (u := o.get("uuid"))})
    g = gather.Gather(server, json.loads(json.dumps(d)), start={}).setup()
    savegame.load(g, json.loads(json.dumps(takeover.state(r, END))))
    return g


def test_the_load_gives_the_orders_of_the_replay():
    r, extra = played()
    g = loaded(r, extra)
    v = g.villagers
    assert v["u1"].tree == r.units[7].tree and v["u1"].state != "idle" and v["u1"].res == "wood"
    assert v["u3"].site is not None and v["u3"].site["name"] == "HOUSE" and v["u3"].state != "idle"
    assert g.stances == {"m1": "defensive"}
    assert g.garrisons == {RECT: ["u2"]}
    q, = g.queues.values()
    assert [x["name"] for x in q] == ["VILLAGER_MALE"] and 0 < q[0]["progress"] < 1


def test_a_unit_with_no_order_is_idle():
    r, extra = played()
    v = loaded(r, extra).villagers["u4"]
    assert (v.state, v.tree, v.site) == ("idle", None, None)
