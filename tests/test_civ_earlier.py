"""game/civs.py EARLIER: some civilizations get some buildings, units and technologies one age earlier, as in AoE2 DE
(#2268, epic #1088): the key "earlier" of game/data/civs.jsonl, read by build.locked and train.unlocked. The cases come
from the data."""
import pytest
from test_gather import FakeServer, grid
from test_train_castle import menus

from game import civs, gather, train

build = train.build                                                    # the module that train uses
EARLY = [(c, n) for c, s in sorted(civs.EARLIER.items()) for n in sorted(s)]
RAM = ("SIEGE_WORKSHOP", "BATTERING_RAM", "CAPPED_RAM_UPGRADE")


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


def other(*names):
    """A civilization that has the names, but none of them earlier."""
    return next(r["name"] for r in civs.ROWS if not set(names) & civs.EARLIER.get(r["name"], set())
                and not any(r["name"] in civs.MISSING.get(n, ()) for n in names))


def ram(server):
    """The menu text of the battering ram (item 0 of the siege workshop)."""
    return menus(server)[0].split(" 1:")[0]


@pytest.mark.parametrize("civ", [c for c, s in sorted(civs.EARLIER.items()) if set(RAM) <= s])
def test_a_player_in_the_feudal_age_has_the_siege_workshop_and_the_battering_ram(civ):
    server, g = setup(civ, 1)
    assert build.locked(g, "SIEGE_WORKSHOP") is None and build.locked(g, "BATTERING_RAM") is None
    slot = build.MENU.index("SIEGE_WORKSHOP")
    assert build.items(g)[slot][1] != build.LOCKED
    train.open_menu(g, "Steve", (12, 4))
    assert "Needs" not in ram(server) and ":gray_dye:" not in ram(server)
    assert not train.unlocked(g, "CAPPED_RAM_UPGRADE")                 # the Castle Age, one age earlier than others
    assert train.unlocked(setup(civ, 2)[1], "CAPPED_RAM_UPGRADE")


def test_another_player_in_the_feudal_age_does_not():
    server, g = setup(other(*RAM), 1)
    assert build.locked(g, "SIEGE_WORKSHOP") is not None and build.locked(g, "SIEGE_WORKSHOP") == build.locked(g, "BATTERING_RAM")
    assert build.items(g)[build.MENU.index("SIEGE_WORKSHOP")][1] == build.LOCKED
    train.open_menu(g, "Steve", (12, 4))
    assert ram(server).endswith(build.locked(g, "BATTERING_RAM")) and ":gray_dye:" in ram(server)
    assert not train.unlocked(setup(other(*RAM), 2)[1], "CAPPED_RAM_UPGRADE")


@pytest.mark.parametrize("civ, name", [(c, n) for c, n in EARLY if n in train.TECHS])
def test_a_technology_comes_one_age_earlier_only_for_its_civilization(civ, name):
    ages = train.BY_KEY["age"][name] - 1

    def g(civ, ages):
        _, g = setup(civ, ages)
        g.techs.update([train.BY_KEY["after"][name]] if name in train.BY_KEY["after"] else [])   # Man-at-Arms before Long Swordsman
        return g
    assert train.unlocked(g(civ, ages), name)
    assert not train.unlocked(g(civ, ages - 1), name)
    assert not train.unlocked(g(other(name), ages), name)


@pytest.mark.parametrize("civ, name", [(c, n) for c, n in EARLY if n not in train.TECHS])
def test_a_unit_or_building_comes_one_age_earlier_only_for_its_civilization(civ, name):
    ages = build.AGE[name] - 1

    def g(civ):
        _, g = setup(civ, ages)
        g.techs.update([build.NEEDS[name]] if name in build.NEEDS else [])   # Chemistry before the hand cannoneer
        return g
    assert build.locked(g(civ), name) is None
    assert build.locked(g(other(name)), name) is not None


def test_the_khitan_heavy_cavalry_archer_upgrade_costs_less():
    base = train.price(setup("BRITONS", 2)[1], "HEAVY_CAVALRY_ARCHER_UPGRADE")
    khitan = train.price(setup("KHITANS", 2)[1], "HEAVY_CAVALRY_ARCHER_UPGRADE")
    assert all(khitan.get(r, 0) <= v for r, v in base.items()) and khitan != base
