"""A saved game keeps the relics and the monk orders (#2412, epic #2253): after a load a relic stays in its monastery
or with its monk, the monastery gives its gold, and a monk that converts or rests goes on. Fake server."""
import json

from test_gather import grid
from test_monk_heal import HealServer

from game import gather, monk, savegame

HOME = (14, 18, 2, 6)                                                  # the monastery footprint x0, x1, z0, z1


def setup():
    """A flat 24 × 24 map (tile size 1): two relics, an own monastery and three own monks."""
    objects = [*({"kind": "unit", "name": "MONK", "player": 1, "uuid": u, "tile": [5.5, z]}
                 for u, z in (("carrier", 5.5), ("convert", 8.5), ("rest", 11.5))),
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 5.5]},
               {"kind": "other", "name": "RELIC", "player": 0, "tile": [10.5, 9.5]},
               {"kind": "building", "name": "MONASTERY", "player": 1, "footprint": [14, 2, 18, 6]}]
    server = HealServer({u: {"Pos": (5.5, 64.0, z), "Health": 30.0, "Max": 30.0}
                         for u, z in (("carrier", 5.5), ("convert", 8.5), ("rest", 11.5))})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.paper = True
    return server, g


def played():
    """Relic 0 in the monastery, relic 1 with its monk, one monk that converts and one that rests."""
    _, g = setup()
    monk.relics(g)[0].update(at=None, home=HOME)
    g.relics[1].update(at=None, monk="carrier")
    g.carrier_at["carrier"] = (5.5, 64.0, 5.5)
    g.converting["convert"] = ["enemy", 2.0, 1]
    g.faith["rest"] = 40.0
    return g


def loaded(g):
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g), sort_keys=True)))
    return h


def test_a_loaded_game_keeps_the_relics_and_the_monk_orders():
    g = played()
    h = loaded(g)
    assert monk.relics(h) == g.relics and h.relics[0]["home"] == HOME     # not the start tiles of aoe2mc.json
    assert monk.carriers(h) == {"carrier": 1}
    assert h.converting == {"convert": ["enemy", 2.0, 1]} and h.faith == {"rest": 40.0}


def test_the_monastery_gives_gold_and_the_rest_goes_on_after_the_load():
    h = loaded(played())
    gold = h.stock["gold"]
    for _ in range(60):
        monk.relic_tick(h, monk.EVERY)
    assert h.stock["gold"] - gold == round(60 * monk.EVERY * monk.GOLD)  # monk.GOLD per AoE2 second of the one relic
    h.converting = {}
    monk.convert(h, 10)
    assert h.faith == {"rest": 30.0}


def test_a_save_before_2412_loads_with_the_start_relics():
    _, g = setup()
    d = savegame.dump(g)
    for p in d["players"].values():
        for f in savegame.MONK:
            p.pop(f, None)
    _, h = setup()
    savegame.load(h, json.loads(json.dumps(d)))
    assert [r["at"] for r in monk.relics(h)] == [(10, 5), (10, 9)] and h.converting == {} and h.faith == {}
