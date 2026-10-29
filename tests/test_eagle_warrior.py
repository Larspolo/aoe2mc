"""game/train.py: the barracks trains the eagle scout and upgrades it to the eagle warrior and the elite eagle warrior
(#1555): for the civilizations of civs.EAGLES. The eagle scout trains faster from the Castle Age (train.BY_KEY["faster"])
and hits harder."""
from test_forging import menus, setup

from game import combat, train

BARRACKS = (17, 3)


def entry(g, name, state):
    """The menu item of name with its cost and time for the player of g."""
    slot, icon, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f" {slot}:{icon}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def player(civ="MAYANS", ages=("FEUDAL_AGE",)):
    server, g = setup()
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_eagle_scout_trains_faster_and_hits_harder_from_the_castle_age():
    server, g = player()
    feudal, s = train.seconds(g, "EAGLE_SCOUT"), train.stats(g, "EAGLE_SCOUT")
    assert feudal == train.TRAIN_TIMES["EAGLE_SCOUT"]
    assert train.order(g, "Steve", train.open_menu(g, "Steve", BARRACKS), train.ITEMS["EAGLE_SCOUT"][0]) == 1
    uuid, = train.tick(g, feudal)
    assert g.soldiers[uuid] == "EAGLE_SCOUT"
    g.techs.add("CASTLE_AGE")
    assert train.seconds(g, "EAGLE_SCOUT") == train.BY_KEY["faster"]["EAGLE_SCOUT"][1] < feudal
    assert train.stats(g, "EAGLE_SCOUT").attack > s.attack
    train.open_menu(g, "Steve", BARRACKS)
    assert entry(g, "EAGLE_SCOUT", "queue 0/15") in menus(server)[-1]
    assert entry(g, "EAGLE_WARRIOR_UPGRADE", "research") in menus(server)[-1]


def test_the_upgrades_change_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "EAGLE_SCOUT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for one more unit
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.order(g, "Steve", rect, train.MORE) == 1
    train.tick(g, train.TRAIN_TIMES["EAGLE_WARRIOR_UPGRADE"])
    assert "EAGLE_WARRIOR_UPGRADE" in g.techs and g.soldiers["e"] == "EAGLE_WARRIOR"
    assert combat.label_command("e", "EAGLE_WARRIOR") in server.log
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert entry(g, "EAGLE_WARRIOR", "queue 0/15") in menu
    assert entry(g, "ELITE_EAGLE_WARRIOR_UPGRADE", "research") in menu
    assert train.order(g, "Steve", rect, train.MORE) == 1
    train.tick(g, train.TRAIN_TIMES["ELITE_EAGLE_WARRIOR_UPGRADE"])
    assert g.soldiers["e"] == "ELITE_EAGLE_WARRIOR"
    train.open_menu(g, "Steve", BARRACKS)
    assert entry(g, "ELITE_EAGLE_WARRIOR", "queue 0/15") in menus(server)[-1]
    assert train.order(g, "Steve", rect, train.ITEMS["ELITE_EAGLE_WARRIOR"][0]) == 1
    uuid, = train.tick(g, train.seconds(g, "ELITE_EAGLE_WARRIOR"))
    assert g.soldiers[uuid] == "ELITE_EAGLE_WARRIOR"
