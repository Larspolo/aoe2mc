"""game/civs.py EARLIER: six civilizations get some buildings, units and technologies one age earlier, as in AoE2 DE
(#2268, epic #1088): the key "earlier" of game/data/civs.jsonl, read by build.locked and train.unlocked."""
import pytest
from test_gather import FakeServer, grid
from test_train_castle import menus

from game import civs, gather, train

build = train.build                                                    # the module that train uses


def setup(civ, ages):
    """A flat 24 × 24 map: a town center and a siege workshop of player 1; the player has researched ages ages."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "SIEGE_WORKSHOP", "player": 1, "tile": [12.0, 4.0],
                "footprint": [10, 2, 14, 6]}]
    data = grid([[64] * 24 for _ in range(24)], objects) | {"players": {"1": {"civ": civ, "color": "blue"}}}
    server = FakeServer({"Steve": {"Pos": (12.0, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, data, start={}).setup()
    g.techs.update(build.AGE_TECHS[:ages])
    return server, g


def ram(server):
    """The menu text of the battering ram (item 0 of the siege workshop)."""
    return menus(server)[0].split(" 1:")[0]


def test_a_cuman_player_in_the_feudal_age_has_the_siege_workshop_and_the_battering_ram():
    server, g = setup("CUMANS", 1)
    assert build.locked(g, "SIEGE_WORKSHOP") is None and build.locked(g, "BATTERING_RAM") is None
    slot = build.MENU.index("SIEGE_WORKSHOP")
    assert build.items(g)[slot][1] != build.LOCKED
    train.open_menu(g, "Steve", (12, 4))
    assert "Needs" not in ram(server) and ":gray_dye:" not in ram(server)
    assert not train.unlocked(g, "CAPPED_RAM_UPGRADE")                 # the Castle Age, one age earlier than others
    assert train.unlocked(setup("CUMANS", 2)[1], "CAPPED_RAM_UPGRADE")


def test_a_frankish_player_in_the_feudal_age_does_not():
    server, g = setup("FRANKS", 1)
    assert build.locked(g, "SIEGE_WORKSHOP") == "Needs the Castle Age" == build.locked(g, "BATTERING_RAM")
    assert build.items(g)[build.MENU.index("SIEGE_WORKSHOP")][1] == build.LOCKED
    train.open_menu(g, "Steve", (12, 4))
    assert ram(server).endswith("Needs the Castle Age") and ":gray_dye:" in ram(server)
    assert not train.unlocked(setup("FRANKS", 2)[1], "CAPPED_RAM_UPGRADE")


@pytest.mark.parametrize("civ, ages, name", [("PERSIANS", 2, "PARTHIAN_TACTICS"), ("JURCHENS", 2, "SIEGE_ENGINEERS"),
                                             ("BOHEMIANS", 2, "CHEMISTRY"), ("KHITANS", 2, "HEAVY_CAVALRY_ARCHER_UPGRADE"),
                                             ("ARMENIANS", 1, "PIKEMAN_UPGRADE"), ("ARMENIANS", 1, "LONG_SWORDSMAN_UPGRADE")])
def test_a_technology_comes_one_age_earlier_only_for_its_civilization(civ, ages, name):
    def g(civ, ages):
        _, g = setup(civ, ages)
        g.techs.update([train.BY_KEY["after"][name]] if name in train.BY_KEY["after"] else [])   # Man-at-Arms before Long Swordsman
        return g
    assert train.unlocked(g(civ, ages), name)
    assert not train.unlocked(g(civ, ages - 1), name)
    assert not train.unlocked(g("BRITONS", ages), name)


def test_an_armenian_player_has_the_spearman_in_the_dark_age():
    assert build.locked(setup("ARMENIANS", 0)[1], "SPEARMAN") is None
    assert build.locked(setup("BRITONS", 0)[1], "SPEARMAN") == "Needs the Feudal Age"
    assert build.locked(setup("ARMENIANS", 2)[1], "CHAMPION") is None                 # the unit of the upgrade too
    assert build.locked(setup("BRITONS", 2)[1], "CHAMPION") == "Needs the Imperial Age"


def test_a_bohemian_player_has_the_hand_cannoneer_in_the_castle_age():
    _, g = setup("BOHEMIANS", 2)
    assert build.AGE["HAND_CANNONEER"] - civs.earlier(g, "HAND_CANNONEER") == 2
    g.techs.add("CHEMISTRY")
    assert build.locked(g, "HAND_CANNONEER") is None
    assert build.locked(setup("BRITONS", 2)[1], "HAND_CANNONEER") == "Needs the Imperial Age"


def test_the_khitan_heavy_cavalry_archer_upgrade_costs_half():
    base = train.price(setup("BRITONS", 2)[1], "HEAVY_CAVALRY_ARCHER_UPGRADE")
    assert train.price(setup("KHITANS", 2)[1], "HEAVY_CAVALRY_ARCHER_UPGRADE") == {r: v // 2 for r, v in base.items()}
