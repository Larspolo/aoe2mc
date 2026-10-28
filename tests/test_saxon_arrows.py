"""Saxon towers and castles fire +100 % base arrows from the Castle Age (#2178, AoE2 DE wiki "Saxons", civilization
bonuses): civs.ARROWS (the key "arrows" of game/data/civs.jsonl) gives the factor of garrison.BASE in each age."""
from test_build_done import DOWN
from test_build_site import Server
from test_garrison_game import TOWER, setup
from test_gather import grid

from game import build, civs, combat, garrison, gather, train


def player(civ, *ages):
    g = gather.Gather.__new__(gather.Gather)
    g.data, g.player, g.techs = {"players": {"1": {"civ": civ}}}, 1, set(build.AGE_TECHS[:len(ages)])
    return g


def test_twice_the_base_arrows_from_the_castle_age():
    feudal, castle, imperial = player("SAXONS", 1), player("SAXONS", 1, 2), player("SAXONS", 1, 2, 3)
    assert [civs.arrows(g, "WATCH_TOWER") for g in (feudal, castle, imperial)] == [1, 2, 2]
    assert garrison.arrows("CASTLE", [], civs.arrows(castle, "CASTLE")) == 2 * garrison.BASE["CASTLE"]
    assert garrison.arrows("KEEP", ["VILLAGER"], civs.arrows(castle, "KEEP")) == 3           # 2 base + 1 villager
    assert civs.arrows(castle, "TOWN_CENTER") == 1                                          # not the town center


def test_other_civilizations_keep_their_arrows():
    for civ in ("BRITONS", "FRANKS", None):
        g = player(civ, 1, 2, 3)
        assert civs.arrows(g, "WATCH_TOWER") == civs.arrows(g, "CASTLE") == 1


def test_the_castle_age_gives_the_saxon_tower_its_new_arrows():
    server, g = setup()
    g.data["players"] = {"1": {"civ": "SAXONS"}}
    uuid = combat.target_uuid([TOWER[0], TOWER[2], TOWER[1], TOWER[3]])
    train.research(g, {"name": "FEUDAL_AGE"})
    assert f"aoe arrows {uuid} 2" not in server.log                     # the Feudal Age: still 1
    train.research(g, {"name": "CASTLE_AGE"})
    assert f"aoe arrows {uuid} 2" in server.log


def test_the_castle_age_does_not_change_a_frankish_tower():
    server, g = setup()
    g.data["players"] = {"1": {"civ": "FRANKS"}}
    train.research(g, {"name": "FEUDAL_AGE"})
    train.research(g, {"name": "CASTLE_AGE"})
    assert not [c for c in server.log if c.startswith("aoe arrows")]


def complete_tower(civ, ages):
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western", "civ": civ}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (40.5, 64.0, 40.5)}},
                    chosen=build.MENU.index("WATCH_TOWER") + 1)
    g = gather.Gather(server, data).setup()
    g.techs |= set(ages)
    g.stock.update(wood=35, stone=125)
    g.click("Steve")
    site, = g.sites
    build.rise(g, site, 80)
    x0, x1, z0, z1 = site["footprint"]
    return server, combat.target_uuid([x0, z0, x1, z1])


def test_a_saxon_tower_built_in_the_castle_age_shoots_2_arrows():
    server, uuid = complete_tower("SAXONS", ["FEUDAL_AGE", "CASTLE_AGE"])
    assert f"aoe arrows {uuid} 2" in server.log


def test_a_saxon_tower_built_in_the_feudal_age_shoots_1_arrow():
    server, uuid = complete_tower("SAXONS", ["FEUDAL_AGE"])
    assert f"aoe arrows {uuid} 1" in server.log
