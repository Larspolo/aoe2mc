"""The regional ships of the dock (#1935): the Thirisadai (Dravidians), the Dragon Ship (Chinese: Heavy Warships, in
place of the fast fire ship), the Dromon, the Lou Chuan and the Catapult Galleon, in the Imperial Age, only for their
civilizations (the costs, times and civilizations of game/data/train.jsonl). AoE2 rules that are not here: the 4 extra
arrows of the Thirisadai, the 5 projectiles of the Dromon (one of them), the anti-unit attack of the Lou Chuan (its
anti-building attack only)."""
import pytest
from test_dock_train import DOCK
from test_heavy_warships import imperial
from test_train_archery import menus

from game import civs, train

build = train.build
SHIPS = ("CATAPULT_GALLEON", "DROMON", "LOU_CHUAN", "THIRISADAI")      # the regional ships of the dock menu
ALL = {c["name"] for c in civs.ROWS}


def have(name):
    """The civilizations that have the item name (game/data/train.jsonl, civs.MISSING)."""
    return ALL - set(civs.MISSING.get(name, ()))


@pytest.mark.parametrize("name", SHIPS)
def test_each_ship_shows_in_the_dock_of_its_civs_in_the_imperial_age(name):
    cost, time = train.COSTS[name], train.TRAIN_TIMES[name]
    slot, item, label = train.ITEMS[name]
    for civ in sorted(have(name)):
        server, g = imperial(civ)
        train.open_menu(g, "Steve", (15, 12))
        own = train.civs.cost(g, name, cost)                           # the Wei: a Lou Chuan costs -25 % (#2246)
        price = " · ".join(f"{own[k]} {k}" for k in ("wood", "gold"))
        t = round(time / train.civs.train_rate(g, name), 1)            # the Aztecs: 15 % faster (#1927)
        assert f"{slot}:{item}:{label}:{price} · {t:g} s · queue 0/15" in menus(server)[-1], civ
    server, g = imperial(sorted(have(name))[0])
    g.techs -= {build.AGE_TECHS[2]}                                       # the Castle Age: a gray item
    train.open_menu(g, "Steve", (15, 12))
    assert f"{slot}:gray_dye:{label}:" in menus(server)[-1]
    for civ in sorted(ALL - have(name))[:3]:
        server, g = imperial(civ)
        train.open_menu(g, "Steve", (15, 12))
        assert f":{label}:" not in menus(server)[-1], civ


def test_the_dock_trains_a_lou_chuan_for_the_chinese():
    server, g = imperial("CHINESE")
    train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", DOCK, train.ITEMS["LOU_CHUAN"][0]) == 1
    ship, = train.tick(g, train.TRAIN_TIMES["LOU_CHUAN"])
    assert g.soldiers[ship] == "LOU_CHUAN" and ship in g.ships


def test_heavy_warships_gives_the_chinese_the_dragon_ship_and_the_others_the_fast_fire_ship():
    for civ, new in (("CHINESE", "DRAGON_SHIP"), ("BRITONS", "FAST_FIRE_SHIP")):
        server, g = imperial(civ, ["MEDIUM_WARSHIPS"])
        g.soldiers |= {"fire": "FIRE_SHIP"}
        for u in g.soldiers:                                             # alive at the census (#3122)
            g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
        train.open_menu(g, "Steve", (15, 12))
        assert train.order(g, "Steve", DOCK, 3) == 1
        train.tick(g, 65)
        assert g.soldiers["fire"] == new, civ
        train.open_menu(g, "Steve", (15, 12))
        label = {"DRAGON_SHIP": "Dragon Ship", "FAST_FIRE_SHIP": "Fast Fire Ship"}[new]
        assert f"6:{train.ITEMS[new][1]}:{label}:" in menus(server)[-1], civ
        assert ":Fire Ship:" not in menus(server)[-1]
