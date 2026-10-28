"""The regional ships of the dock (#1935): the Thirisadai (Dravidians), the Dragon Ship (Chinese: Heavy Warships, in
place of the fast fire ship), the Dromon, the Lou Chuan and the Catapult Galleon, in the Imperial Age, only for their
civilizations. Values: the AoE2 DE wiki infoboxes (MediaWiki API, 2026-10-27) and the availability chart of the
Catapult Galleon. AoE2 rules that are not here: the 4 extra arrows of the Thirisadai, the 5 projectiles of the Dromon
(one of them), the anti-unit attack of the Lou Chuan (its anti-building attack only)."""
import pytest
from test_dock_train import DOCK
from test_heavy_warships import imperial
from test_train_archery import menus

from game import civs, combat, fleet, train

build = train.build
WIKI = {   # cost, time, hp, civilizations
    "THIRISADAI": ({"wood": 180, "gold": 60}, 40, 250, {"DRAVIDIANS"}),
    "DRAGON_SHIP": ({"wood": 75, "gold": 45}, 27, 135, {"CHINESE"}),
    "DROMON": ({"wood": 175, "gold": 150}, 65, 125, {"ARMENIANS", "BYZANTINES", "GOTHS", "HUNS", "ROMANS"}),
    "LOU_CHUAN": ({"wood": 250, "gold": 225}, 60, 175, {"CHINESE", "JURCHENS", "SHU", "WEI", "WU"}),
    "CATAPULT_GALLEON": ({"wood": 225, "gold": 100}, 55, 140, {"AZTECS", "CUMANS", "DANES", "INCAS", "MAPUCHE",
                                                              "MAYANS", "MUISCA", "SAXONS", "TUPI", "VARANGIANS",
                                                              "VIKINGS"}),
}
LABELS = {"THIRISADAI": "Thirisadai", "DROMON": "Dromon", "LOU_CHUAN": "Lou Chuan", "CATAPULT_GALLEON": "Catapult Galleon"}


def test_the_values_are_those_of_the_wiki():
    every = set().union(*civs.MISSING.values())
    for name, (cost, time, hp, have) in WIKI.items():
        assert (train.COSTS[name], train.TRAIN_TIMES[name], combat.stats(name).hp) == (cost, time, hp), name
        assert name not in build.NEEDS and len(train.HELP[name]) <= 50
        assert every - set(civs.MISSING[name]) == have, name
        assert combat.SHIP in combat.stats(name).classes and name in fleet.SPEEDS, name
    assert set(LABELS) <= set(train.TRAINS["DOCK"]) and "DRAGON_SHIP" not in train.TRAINS["DOCK"]
    assert combat.MIN_RANGE["LOU_CHUAN"] == 3
    assert combat.MIN_RANGE["DROMON"] == 3
    assert combat.MIN_RANGE["CATAPULT_GALLEON"] == 3
    assert "unique" in combat.stats("THIRISADAI").classes
    assert "fireship" in combat.stats("DRAGON_SHIP").classes
    assert combat.damage("CATAPULT_GALLEON", "HOUSE") == 30 + 130 - combat.stats("HOUSE").melee   # melee damage


@pytest.mark.parametrize("name", sorted(LABELS))
def test_each_ship_shows_in_the_dock_of_its_civs_in_the_imperial_age(name):
    cost, time, _, have = WIKI[name]
    slot, item = train.ITEMS[name][:2]
    for civ in sorted(have):
        server, g = imperial(civ)
        train.open_menu(g, "Steve", (15, 12))
        own = train.civs.cost(g, name, cost)                           # the Wei: a Lou Chuan costs -25 % (#2246)
        price = " · ".join(f"{own[k]} {k}" for k in ("wood", "gold"))
        t = round(time / train.civs.train_rate(g, name), 1)            # the Aztecs: 15 % faster (#1927)
        assert f"{slot}:{item}:{LABELS[name]}:{price} · {t:g} s · queue 0/15" in menus(server)[-1], civ
    server, g = imperial(sorted(have)[0])
    g.techs -= {build.AGE_TECHS[2]}                                       # the Castle Age: a gray item
    train.open_menu(g, "Steve", (15, 12))
    assert f"{slot}:gray_dye:{LABELS[name]}:" in menus(server)[-1]
    for civ in ("BRITONS", "FRANKS", "DRAVIDIANS" if name != "THIRISADAI" else "CHINESE"):
        server, g = imperial(civ)
        train.open_menu(g, "Steve", (15, 12))
        assert f":{LABELS[name]}:" not in menus(server)[-1], civ


def test_the_dock_trains_a_lou_chuan_for_the_chinese():
    server, g = imperial("CHINESE")
    train.open_menu(g, "Steve", (15, 12))
    assert train.order(g, "Steve", DOCK, train.ITEMS["LOU_CHUAN"][0]) == 1
    ship, = train.tick(g, 60)
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
