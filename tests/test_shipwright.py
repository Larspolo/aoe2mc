"""Shipwright at the university (#1490): Imperial Age, 1000 food, 300 gold, 60 s (AoE2 DE wiki "Shipwright", at the
university since The Last Chieftains); after it, the ships of the dock cost 20 % less wood and train 54 % faster. The
technologies of the dock do not change. Fake server."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import build, civs, train

UNIVERSITY = {"kind": "building", "name": "UNIVERSITY", "player": 1, "tile": [8.0, 18.0], "footprint": [6, 16, 10, 20]}


def imperial(civ="BRITONS", techs=()):
    server, g = dock_map(wood=1000)
    g.data["players"]["1"]["civ"] = civ
    g.data["objects"].append(dict(UNIVERSITY))
    g.techs |= set(build.AGE_TECHS[:3]) | set(techs)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert "SHIPWRIGHT" in train.TRAINS["UNIVERSITY"] and len(train.HELP["SHIPWRIGHT"]) <= 50
    assert train.SHIPWRIGHT == (0.8, 1.54)


def test_the_university_has_it_only_in_the_imperial_age_and_not_for_the_franks():
    server, g = imperial()
    g.stock.update(food=1000, gold=300)
    rect = train.open_menu(g, "Steve", (8, 18))
    assert "18:book:Shipwright:1000 food · 300 gold · 60 s" in menus(server)[-1]
    assert train.order(g, "Steve", rect, train.MORE) == 1 and g.stock["food"] == g.stock["gold"] == 0
    train.tick(g, 59.9)
    assert "SHIPWRIGHT" not in g.techs                                 # a technology: not faster
    train.tick(g, 0.2)
    assert "SHIPWRIGHT" in g.techs
    g.techs.discard("IMPERIAL_AGE")
    assert not train.unlocked(g, "SHIPWRIGHT")
    server, g = imperial("FRANKS")                                     # the wiki availability chart
    assert "FRANKS" in civs.MISSING["SHIPWRIGHT"] and not train.unlocked(g, "SHIPWRIGHT")


def test_after_it_the_ships_cost_20_percent_less_wood():
    server, g = imperial()
    before = {n: train.price(g, n) for n in ("FISHING_SHIP", "GALLEY", "GILLNETS", "ARCHER")}
    g.techs.add("SHIPWRIGHT")
    assert train.price(g, "FISHING_SHIP") == {"wood": 60} and before["FISHING_SHIP"] == {"wood": 75}
    assert train.price(g, "GALLEY") == {"wood": 72, "gold": before["GALLEY"]["gold"]}
    assert train.price(g, "GILLNETS") == before["GILLNETS"] and train.price(g, "ARCHER") == before["ARCHER"]
    rect = train.open_menu(g, "Steve", (15, 12))
    assert "0:oak_boat:Fishing Ship:60 wood" in menus(server)[-1] and train.order(g, "Steve", rect, 0) == 1
    assert g.stock["wood"] == 940


def takes(g, rect, seconds):
    """True when the queue of rect is still busy 0.1 s before seconds and empty 0.1 s after them."""
    train.tick(g, seconds - 0.1)
    busy = bool(g.queues[rect])
    train.tick(g, 0.2)
    return busy and not g.queues[rect]


def test_after_it_the_dock_trains_ships_54_percent_faster():
    server, g = imperial()
    t = train.TRAIN_TIMES["FISHING_SHIP"]
    assert train.queue(g, "Steve", (15, 12), "FISHING_SHIP") and takes(g, DOCK, t)
    g.techs.add("SHIPWRIGHT")
    assert train.queue(g, "Steve", (15, 12), "FISHING_SHIP") and takes(g, DOCK, t / 1.54)
