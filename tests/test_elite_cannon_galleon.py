"""Elite Cannon Galleon (#1491): the dock researches the upgrade in the Imperial Age after Chemistry (525 wood, 500 gold,
30 s: the UpCost and UpTime of the AoE2 DE wiki infobox "Cannon Galleon"). Then the live cannon galleons are elite
cannon galleons (wiki "Elite Cannon Galleon": HP 150, MAttack 60, +275 vs. buildings, +25 vs. siege, Range 15, MinRange
3, Armor 0/6, LOS 17, ROF 10, Speed 1.05, AOE 0.3), and the dock trains them in the slot of the cannon galleon. Only the
civilizations with it in the wiki chart (1, x, +) see it."""
import buildings
from game import civs, combat, train
from test_dock_train import DOCK, dock_map
from test_train_archery import menus

build = train.build                                                    # the module that train uses
HAVE = {"BENGALIS", "BERBERS", "BOHEMIANS", "BURGUNDIANS", "BURMESE", "DRAVIDIANS", "HINDUSTANIS", "ITALIANS",
        "JAPANESE", "KHMER", "KOREANS", "LITHUANIANS", "MALAY", "PERSIANS", "PORTUGUESE", "SARACENS", "SPANISH", "TATARS",
        "TURKS", "VIETNAMESE"}


def imperial(civ="SPANISH"):
    server, g = dock_map(wood=2000)
    g.data["players"] = {"1": {"civ": civ}}
    g.techs |= set(build.AGE_TECHS[:3])
    g.stock["gold"] = 2000
    return server, g


def test_the_values_are_those_of_aoe2():
    assert train.BY_KEY["after"]["ELITE_CANNON_GALLEON_UPGRADE"] == "CHEMISTRY" and len(train.HELP["ELITE_CANNON_GALLEON_UPGRADE"]) <= 50
    assert combat.BLAST["ELITE_CANNON_GALLEON"] == 0.3 and combat.MIN_RANGE["ELITE_CANNON_GALLEON"] == 3
    assert "ELITE_CANNON_GALLEON" in combat.MELEE_RANGED and train.ITEMS["ELITE_CANNON_GALLEON"][0] == train.ITEMS["CANNON_GALLEON"][0]
    assert set(civs.MISSING["ELITE_CANNON_GALLEON_UPGRADE"]) == set(buildings.CIV_TO_ARCH) - HAVE
    assert HAVE <= set(buildings.CIV_TO_ARCH)


def test_the_upgrade_is_in_the_dock_menu_in_the_imperial_age_after_chemistry():
    server, g = dock_map()
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE", "CHEMISTRY"}
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1]             # the Castle Age
    server, g = imperial()
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1]             # no Chemistry
    g.techs.add("CHEMISTRY")
    train.open_menu(g, "Steve", (15, 12))
    slot = train.ITEMS["ELITE_CANNON_GALLEON_UPGRADE"][0]
    assert f" {slot}:book:Elite Cannon Galleon:525 wood · 500 gold · 30 s · research " in menus(server)[-1] + " "


def test_a_civilization_without_it_does_not_see_it():
    server, g = imperial("VIKINGS")
    g.techs.add("CHEMISTRY")
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" not in menus(server)[-1] and "Fishing Ship" in menus(server)[-1]
    server, g = imperial("SPANISH")
    g.techs.add("CHEMISTRY")
    train.open_menu(g, "Steve", (15, 12))
    assert "Elite Cannon Galleon" in menus(server)[-1]


def test_the_live_cannon_galleons_become_elite_and_the_dock_trains_them():
    server, g = imperial()
    g.techs.add("CHEMISTRY")
    g.soldiers |= {"cg": "CANNON_GALLEON", "gal": "GALLEY"}
    for u in g.soldiers:                                             # alive at the census (#3122)
        g.game.entities.setdefault(u, {"Pos": (0.5, 64.0, 0.5)})
    slot = train.ITEMS["ELITE_CANNON_GALLEON_UPGRADE"][0]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", (15, 12)), slot) == 1
    assert (g.stock["wood"], g.stock["gold"]) == (2000 - 525, 2000 - 500)
    train.tick(g, 29)
    assert g.soldiers["cg"] == "CANNON_GALLEON"
    train.tick(g, 1)
    assert "ELITE_CANNON_GALLEON_UPGRADE" in g.techs and (g.soldiers["cg"], g.soldiers["gal"]) == ("ELITE_CANNON_GALLEON", "GALLEY")
    assert any(c.startswith("aoe stats cg 150 60 0 6 ") for c in server.log) and "aoe range cg 15 100 0.3 3" in server.log
    assert combat.label_command("cg", "ELITE_CANNON_GALLEON") in server.log
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    cg = train.ITEMS["CANNON_GALLEON"][0]
    assert f"{cg}:dark_oak_boat:Elite Cannon Galleon:200 wood · 150 gold · 46 s · queue 0/15" in menu
    assert ":Cannon Galleon:" not in menu and "research" not in menu.split("Elite Cannon Galleon")[1][:40]
    assert train.order(g, "Steve", DOCK, cg) == 1
    ship, = train.tick(g, 46)
    assert g.soldiers[ship] == "ELITE_CANNON_GALLEON" and ship in g.ships
    assert any(c.startswith(f"aoe range {ship} 15 ") for c in server.log)   # tile size 1: 15 tiles
