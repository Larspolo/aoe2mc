"""game/train.py: the Malay research Thalassocracy in the Castle Age (AoE2 DE wiki, "Unique technology"), #4337: each
own dock becomes a harbor (build.line: the values of the harbor) and shoots 3 more arrows (train.more_arrows)."""
from test_gather import grid
from test_loom import menus
from test_repair import HpServer
from test_tower_upgrades import building, item, research, uuid

from game import build, combat, gather, train

CASTLE, MAP, NEW, OTHER = (8, 12, 8, 12), (16, 17, 16, 17), (18, 19, 4, 5), (20, 21, 20, 21)   # block footprints (x0, x1, z0, z1)


def setup(civ="MALAY"):
    """A flat 24 × 24 map with an own castle and dock, a dock of player 2 and the first two ages, with the stock."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "CASTLE", "player": 1, "tile": [10, 10], "footprint": [8, 8, 12, 12]},
               {"kind": "building", "name": "DOCK", "player": 1, "tile": [16.5, 16.5], "footprint": [16, 16, 17, 17]},
               {"kind": "building", "name": "DOCK", "player": 2, "tile": [20.5, 20.5], "footprint": [20, 20, 21, 21]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"], data["level_height"] = {"1": {"civ": civ, "color": "blue", "arch": "western"}}, 1
    server = HpServer({}, {})
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS[:2])
    g.stock.update(food=10000, wood=10000, gold=10000)
    return server, g


def test_the_castle_menu_of_the_malay_shows_thalassocracy_and_no_other_civilization_does():
    server, g = setup()
    train.open_menu(g, "Steve", (9, 9))
    assert item("THALASSOCRACY") in menus(server)[-1]
    server, g = setup("BRITONS")
    train.open_menu(g, "Steve", (9, 9))
    assert item("THALASSOCRACY") not in menus(server)[-1]


def test_the_research_gives_each_own_dock_the_values_and_the_arrows_of_a_harbor():
    server, g = setup()
    server.hp[uuid(MAP)] = combat.stats("DOCK").hp - 300          # 300 hit points lost
    research(g, "THALASSOCRACY")
    harbor = combat.stats("HARBOR")
    assert server.hp[uuid(MAP)] == harbor.hp - 300                # the lost hit points stay lost
    assert any(c.startswith(building(harbor)) for c in server.log)
    assert f"aoe arrows {uuid(MAP)} 3" in server.log              # no fishing ship: the 3 more arrows
    assert f"aoe label {uuid(MAP)} Harbor" in server.log
    assert not any(uuid(OTHER) in c for c in server.log)          # the dock of player 2 keeps its values


def test_a_dock_built_after_the_research_is_a_harbor():
    server, g = setup()
    g.techs.add("THALASSOCRACY")
    site = build.found(g, "DOCK", NEW)
    server.log.clear()
    build.rise(g, site, float("inf"))
    harbor = combat.stats("HARBOR")
    assert any(c.startswith(f"aoe building {uuid(NEW)} {harbor.hp} {harbor.melee} {harbor.pierce} ") for c in server.log)
    assert any(c.startswith(f"aoe arrows {uuid(NEW)} ") for c in server.log)   # the arrows of the harbor (its data)
