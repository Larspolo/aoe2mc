"""Shipwright at the university (#1490): the Imperial Age (AoE2 DE wiki "Shipwright", at the university since The Last
Chieftains); after it, the ships of the dock cost less wood and train faster (train.SHIPWRIGHT). The technologies of the
dock do not change. Fake server."""
from test_dock_train import DOCK, dock_map

from game import build, train

UNIVERSITY = {"kind": "building", "name": "UNIVERSITY", "player": 1, "tile": [8.0, 18.0], "footprint": [6, 16, 10, 20]}


def imperial(civ="BRITONS", techs=()):
    server, g = dock_map(wood=1000)
    g.data["players"]["1"]["civ"] = civ
    g.data["objects"].append(dict(UNIVERSITY))
    g.techs |= set(build.AGE_TECHS[:3]) | set(techs)
    return server, g


def test_the_university_researches_it_in_the_imperial_age():
    server, g = imperial()
    g.stock.update(train.COSTS["SHIPWRIGHT"])
    rect = train.open_menu(g, "Steve", (8, 18))
    assert train.order(g, "Steve", rect, train.slots("UNIVERSITY", "SHIPWRIGHT")[0]) == 1
    assert all(g.stock[r] == 0 for r in train.COSTS["SHIPWRIGHT"])
    assert takes(g, rect, train.TRAIN_TIMES["SHIPWRIGHT"])               # a technology: not faster
    assert "SHIPWRIGHT" in g.techs
    g.techs.discard("IMPERIAL_AGE")
    assert not train.unlocked(g, "SHIPWRIGHT")


def test_after_it_the_ships_cost_less_wood():
    server, g = imperial()
    before = {n: train.price(g, n) for n in ("FISHING_SHIP", "GALLEY", "GILLNETS", "ARCHER")}
    g.techs.add("SHIPWRIGHT")
    assert train.price(g, "FISHING_SHIP")["wood"] < before["FISHING_SHIP"]["wood"]
    assert train.price(g, "GALLEY")["wood"] < before["GALLEY"]["wood"]
    assert train.price(g, "GALLEY")["gold"] == before["GALLEY"]["gold"]
    assert train.price(g, "GILLNETS") == before["GILLNETS"] and train.price(g, "ARCHER") == before["ARCHER"]
    rect = train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", rect, train.slots("DOCK", "FISHING_SHIP")[0]) == 1
    assert g.stock["wood"] == 1000 - train.price(g, "FISHING_SHIP")["wood"]


def takes(g, rect, seconds):
    """True when the queue of rect is still busy 0.1 s before seconds and empty 0.1 s after them."""
    train.tick(g, seconds - 0.1)
    busy = bool(g.queues[rect])
    train.tick(g, 0.2)
    return busy and not g.queues[rect]


def test_after_it_the_dock_trains_ships_faster():
    server, g = imperial()
    t = train.TRAIN_TIMES["FISHING_SHIP"]
    assert train.queue(g, "Steve", (15, 12), "FISHING_SHIP") and takes(g, DOCK, t)
    g.techs.add("SHIPWRIGHT")
    assert train.queue(g, "Steve", (15, 12), "FISHING_SHIP") and takes(g, DOCK, t / train.SHIPWRIGHT[1])
