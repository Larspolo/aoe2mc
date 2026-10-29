"""game/train.py: the barracks trains the Champi Scout and upgrades it to the Champi Runner, the Champi Warrior and the
Elite Champi Warrior (#2133): the regional infantry of The Last Chieftains, only for some civilizations."""
from test_castle_upgrades import entry
from test_forging import menus, setup

from game import civs, combat, train

BARRACKS = (17, 3)
LINE = ("CHAMPI_SCOUT", "CHAMPI_RUNNER", "CHAMPI_WARRIOR", "ELITE_CHAMPI_WARRIOR")


def player(civ="MAPUCHE", ages=()):
    server, g = setup()
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_help_texts_are_short():
    assert all(len(train.HELP[n]) <= 50 for n in LINE)


def test_the_barracks_menu_has_the_champi_scout_only_for_its_civilizations():
    server, g = player()
    train.open_menu(g, "Steve", BARRACKS)
    assert " " + entry(g, BARRACKS, "CHAMPI_SCOUT") + "queue 0/15" in menus(server)[-1]
    server, g = player(sorted(civs.MISSING["CHAMPI_SCOUT"])[0], ("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", BARRACKS)
    assert "Champi" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "CHAMPI_SCOUT") is None


def test_the_upgrades_change_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["c"] = "CHAMPI_SCOUT"
    g.game.entities.setdefault("c", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for one more unit
    rect = train.open_menu(g, "Steve", BARRACKS)
    for new in LINE[1:]:
        up = f"{new}_UPGRADE"
        train.open_menu(g, "Steve", BARRACKS)
        assert " " + entry(g, BARRACKS, up) + "research" in menus(server)[-1]
        assert train.order(g, "Steve", rect, train.layout(g, rect)[up][0]) == 1
        train.tick(g, train.seconds(g, up))
        assert g.soldiers["c"] == new and combat.label_command("c", new) in server.log
    train.open_menu(g, "Steve", BARRACKS)
    assert " " + entry(g, BARRACKS, "ELITE_CHAMPI_WARRIOR") + "queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, train.layout(g, rect)["ELITE_CHAMPI_WARRIOR"][0]) == 1
    uuid, = train.tick(g, train.seconds(g, "ELITE_CHAMPI_WARRIOR"))
    assert g.soldiers[uuid] == "ELITE_CHAMPI_WARRIOR"
