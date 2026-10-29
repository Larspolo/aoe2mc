"""game/feitoria.py: each complete own Feitoria of the Portuguese adds food, wood, gold and stone over time (#4082)."""
from types import SimpleNamespace

from game import feitoria

WIKI = feitoria.RATE["FEITORIA"]                                       # per AoE2 second (data/buildings.jsonl)


def game(sites=(), objects=(), ruins=()):
    g = SimpleNamespace(player=1, sites=list(sites), data={"objects": list(objects)}, ruins=set(ruins),
                        stock={"food": 0, "wood": 0, "gold": 0, "stone": 0})
    g.earn = lambda res, n: g.stock.__setitem__(res, g.stock[res] + n)
    return g


def site(done=True, name="FEITORIA"):
    return {"name": name, "footprint": [0, 4, 0, 4], "done": done}


def ten_seconds(g):
    for _ in range(40):
        feitoria.tick(g, 0.25)
    return g.stock


def test_a_finished_feitoria_adds_its_rates_in_ten_seconds():
    assert ten_seconds(game([site()])) == {k: int(round(v * 10)) for k, v in WIKI.items()}


def test_two_feitorias_add_twice():
    assert ten_seconds(game([site(), site()])) == {k: int(round(v * 20)) for k, v in WIKI.items()}


def test_a_start_feitoria_adds_and_a_fallen_one_or_a_site_adds_nothing():
    o = {"kind": "building", "name": "FEITORIA", "player": 1, "footprint": [0, 0, 4, 4]}
    assert ten_seconds(game(objects=[o])) == {k: int(round(v * 10)) for k, v in WIKI.items()}
    assert ten_seconds(game(objects=[o], ruins=[(0, 4, 0, 4)])) == dict.fromkeys(WIKI, 0)
    assert ten_seconds(game([site(done=False), site(name="MARKET")])) == dict.fromkeys(WIKI, 0)
    assert ten_seconds(game(objects=[dict(o, player=2)])) == dict.fromkeys(WIKI, 0)

