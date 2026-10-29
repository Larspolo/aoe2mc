"""Saxon towers and castles fire +100 % base arrows from the Castle Age (#2178, AoE2 DE wiki "Saxons", civilization
bonuses): civs.ARROWS (the key "arrows" of game/data/civs.jsonl) gives the factor of garrison.BASE in each age. The
tests compare the `aoe arrows` commands with civs.arrows, not with the values of the data."""
from test_build_done import DOWN
from test_build_site import Server
from test_garrison_game import TOWER, setup
from test_gather import grid

from game import build, civs, combat, garrison, gather, train


def arrows(g):
    """The arrows of an empty own watch tower of g in its present age."""
    return garrison.arrows("WATCH_TOWER", [], civs.arrows(g, "WATCH_TOWER"))


def test_the_castle_age_gives_the_saxon_tower_its_new_arrows():
    server, g = setup()
    g.data["players"] = {"1": {"civ": "SAXONS"}}
    uuid = combat.target_uuid([TOWER[0], TOWER[2], TOWER[1], TOWER[3]])
    for age in ("FEUDAL_AGE", "CASTLE_AGE"):
        n = len(server.log)
        train.research(g, {"name": age})
        assert f"aoe arrows {uuid} {arrows(g)}" in server.log[n:], age


def test_the_castle_age_does_not_change_a_frankish_tower():
    server, g = setup()
    g.data["players"] = {"1": {"civ": "FRANKS"}}
    train.research(g, {"name": "FEUDAL_AGE"})
    train.research(g, {"name": "CASTLE_AGE"})
    assert bool([c for c in server.log if c.startswith("aoe arrows")]) == bool(civs.ARROWS.get("FRANKS"))


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
    return server, g, combat.target_uuid([x0, z0, x1, z1])


def test_a_saxon_tower_built_in_the_castle_age_shoots_the_arrows_of_its_age():
    server, g, uuid = complete_tower("SAXONS", ["FEUDAL_AGE", "CASTLE_AGE"])
    assert f"aoe arrows {uuid} {arrows(g)}" in server.log


def test_a_saxon_tower_built_in_the_feudal_age_shoots_the_arrows_of_its_age():
    server, g, uuid = complete_tower("SAXONS", ["FEUDAL_AGE"])
    assert f"aoe arrows {uuid} {arrows(g)}" in server.log
