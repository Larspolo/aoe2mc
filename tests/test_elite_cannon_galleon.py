"""Elite Cannon Galleon (#1491): the dock researches the upgrade in the Imperial Age after the technology of its "after"
key. Then the live cannon galleons are elite cannon galleons, and the dock trains them in the slot of the cannon
galleon. Only the civilizations with it (civs.MISSING) see it."""
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

from game import civs, combat, train

build = train.build                                                    # the module that train uses
UP = "ELITE_CANNON_GALLEON_UPGRADE"
AFTER = train.BY_KEY["after"][UP]
WITHOUT = sorted(civs.MISSING[UP])[0]
WITH = next(c for c in sorted(r["name"] for r in civs.ROWS) if c not in civs.MISSING[UP] and c not in civs.MISSING.get(AFTER, ()))


def entry(g, name, state):
    """The menu item of name with its cost and time for the player of g."""
    slot, icon, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f" {slot}:{icon}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def imperial(civ=WITH):
    server, g = dock_map(wood=2000)
    g.data["players"] = {"1": {"civ": civ}}
    g.techs |= set(build.AGE_TECHS[:3])
    g.stock["gold"] = 2000
    return server, g


def test_the_upgrade_is_in_the_dock_menu_in_the_imperial_age_after_its_technology():
    server, g = dock_map()
    g.data["players"]["1"]["civ"] = WITH
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", AFTER}
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1]             # the Castle Age
    server, g = imperial()
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1]             # no AFTER
    g.techs.add(AFTER)
    train.open_menu(g, "Steve", (15, 12))
    assert entry(g, UP, "research ") in menus(server)[-1] + " "


def test_a_civilization_without_it_does_not_see_it():
    server, g = imperial(WITHOUT)
    g.techs.add(AFTER)
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1]
    server, g = imperial(WITH)
    g.techs.add(AFTER)
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" in menus(server)[-1]


def test_the_live_cannon_galleons_become_elite_and_the_dock_trains_them():
    server, g = imperial()
    g.techs.add(AFTER)
    g.soldiers |= {"cg": "CANNON_GALLEON", "gal": "GALLEY"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    cost, t = train.COSTS[UP], train.TRAIN_TIMES[UP]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), train.ITEMS[UP][0]) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (2000 - cost.get("wood", 0), 2000 - cost.get("gold", 0))
    train.tick(g, t - 1)
    assert g.soldiers["cg"] == "CANNON_GALLEON"
    train.tick(g, 1)
    assert UP in g.techs and (g.soldiers["cg"], g.soldiers["gal"]) == ("ELITE_CANNON_GALLEON", "GALLEY")
    s = train.stats(g, "ELITE_CANNON_GALLEON")
    assert combat.stats_command("cg", "ELITE_CANNON_GALLEON", s) in server.log
    assert any(c.startswith(f"aoe range cg {s.range} ") for c in server.log)
    assert combat.label_command("cg", "ELITE_CANNON_GALLEON") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    cg = train.ITEMS["CANNON_GALLEON"][0]
    assert entry(g, "ELITE_CANNON_GALLEON", "queue 0/15") in menu and train.ITEMS["ELITE_CANNON_GALLEON"][0] == cg
    assert ":Cannon Galleon:" not in menu and "research" not in menu.split("Elite Cannon Galleon")[1][:40]
    assert train.order(g, "Steve", DOCK, cg) == 1
    ship, = train.tick(g, train.seconds(g, "ELITE_CANNON_GALLEON"))
    assert g.soldiers[ship] == "ELITE_CANNON_GALLEON" and ship in g.ships
    assert any(c.startswith(f"aoe range {ship} {s.range} ") for c in server.log)   # tile size 1: the range in tiles
