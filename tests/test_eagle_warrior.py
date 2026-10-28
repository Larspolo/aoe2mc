"""game/train.py: the barracks trains the eagle scout and upgrades it to the eagle warrior and the elite eagle warrior
(#1555, AoE2 DE wiki infoboxes "Eagle Scout", "Eagle Warrior", "Elite Eagle Warrior"): only the Aztecs and the Mayans
(civs.EAGLES; the Incas lost it in The Last Chieftains). The eagle scout trains in 46 s in the Feudal Age and in 35 s
from the Castle Age (train.BY_KEY["faster"]), with 7 attack and the cavalry, camel and ship bonus from the Castle Age."""
from test_forging import menus, setup

from game import build, civs, combat, train

BARRACKS = (17, 3)


def player(civ="MAYANS", ages=("FEUDAL_AGE",)):
    server, g = setup()
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_values_are_those_of_the_wiki():
    for name in ("EAGLE_SCOUT", "EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR"):
        assert len(train.HELP[name]) <= 50
    assert [train.TRAIN_TIMES[n] for n in ("EAGLE_SCOUT", "EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR")] == [46, 35, 20]
    assert [build.AGE[n] for n in ("EAGLE_SCOUT", "EAGLE_WARRIOR", "ELITE_EAGLE_WARRIOR")] == [1, 2, 3]


def test_the_barracks_menu_has_the_eagle_scout_only_for_the_aztecs_and_the_mayans():
    assert set(civs.EAGLES) == {"AZTECS", "MAYANS"}
    assert {"INCAS", "BRITONS", "FRANKS"} <= set(civs.MISSING["EAGLE_SCOUT"]) and "AZTECS" not in civs.MISSING["EAGLE_SCOUT"]
    for civ in civs.EAGLES:
        server, g = player(civ)
        train.open_menu(g, "Steve", BARRACKS)
        time = {"AZTECS": 40, "MAYANS": 46}[civ]                     # Aztecs: 46 s / 1.15 (#1927)
        assert f" 7:husk_spawn_egg:Eagle Scout:20 food · 50 gold · {time} s · queue 0/15" in menus(server)[-1]
    server, g = player("INCAS")
    train.open_menu(g, "Steve", BARRACKS)
    assert "Eagle" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "EAGLE_SCOUT") is None


def test_the_eagle_scout_trains_faster_and_hits_harder_from_the_castle_age():
    server, g = player()
    assert train.seconds(g, "EAGLE_SCOUT") == 46 and train.stats(g, "EAGLE_SCOUT").attack == 4
    assert train.order(g, "Steve", train.open_menu(g, "Steve", BARRACKS), 7) == 1
    uuid, = train.tick(g, 46)
    assert g.soldiers[uuid] == "EAGLE_SCOUT"
    g.techs.add("CASTLE_AGE")
    assert train.seconds(g, "EAGLE_SCOUT") == 35
    assert train.stats(g, "EAGLE_SCOUT") == combat.stats("EAGLE_SCOUT")._replace(
        attack=7, bonus={"siege": 3, "cavalry": 2, "camel": 1, "ship": 1})
    train.open_menu(g, "Steve", BARRACKS)
    assert " 7:husk_spawn_egg:Eagle Scout:20 food · 50 gold · 35 s · queue 0/15" in menus(server)[-1]
    assert f" {train.MORE}:book:Eagle Warrior:200 food · 200 gold · 50 s · research" in menus(server)[-1]


def test_the_upgrades_change_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "EAGLE_SCOUT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for one more unit
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.order(g, "Steve", rect, train.MORE) == 1
    train.tick(g, 50)
    assert "EAGLE_WARRIOR_UPGRADE" in g.techs and g.soldiers["e"] == "EAGLE_WARRIOR"
    assert combat.label_command("e", "EAGLE_WARRIOR") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert " 7:husk_spawn_egg:Eagle Warrior:20 food · 50 gold · 35 s · queue 0/15" in menu
    assert f" {train.MORE}:book:Elite Eagle Warrior:800 food · 500 gold · 50 s · research" in menu
    assert train.order(g, "Steve", rect, train.MORE) == 1
    train.tick(g, 50)
    assert g.soldiers["e"] == "ELITE_EAGLE_WARRIOR"
    train.open_menu(g, "Steve", BARRACKS)
    assert " 7:husk_spawn_egg:Elite Eagle Warrior:20 food · 50 gold · 20 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 7) == 1
    uuid, = train.tick(g, 20)
    assert g.soldiers[uuid] == "ELITE_EAGLE_WARRIOR"
