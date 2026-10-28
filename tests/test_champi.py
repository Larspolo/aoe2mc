"""game/train.py: the barracks trains the Champi Scout and upgrades it to the Champi Runner, the Champi Warrior and the
Elite Champi Warrior (#2133, AoE2 DE wiki infoboxes "Champi Scout", "Champi Runner", "Champi Warrior", "Elite Champi
Warrior"): only the Incas, Mapuche, Muisca and Tupi, the regional infantry of The Last Chieftains."""
from test_forging import menus, setup

from game import ai, build, civs, combat, train

BARRACKS = (17, 3)
LINE = ("CHAMPI_SCOUT", "CHAMPI_RUNNER", "CHAMPI_WARRIOR", "ELITE_CHAMPI_WARRIOR")
CIVS = {"INCAS", "MAPUCHE", "MUISCA", "TUPI"}


def player(civ="MAPUCHE", ages=()):
    server, g = setup()
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_values_are_those_of_the_wiki():
    assert all(len(train.HELP[n]) <= 50 for n in LINE)                # the costs and times: the menu tests (#2182)
    assert [build.AGE.get(n, 0) for n in LINE] == [0, 1, 2, 3]
    assert [tuple(combat.stats(n)[:6]) for n in LINE] == [(35, 3, 0, 2, 0, 2.0), (40, 5, 0, 2, 0, 2.0),
                                                          (55, 9, 0, 3, 0, 2.0), (65, 11, 0, 4, 0, 2.0)]
    assert combat.stats("CHAMPI_SCOUT").bonus == {"camel": 2, "cavalry": 2, "siege": 2}
    assert combat.stats("ELITE_CHAMPI_WARRIOR").bonus == {"siege": 3, "standard": 3}
    assert [combat.SIGHT[n] for n in LINE] == [5, 5, 6, 6]
    assert ai.walk_speed("CHAMPI_SCOUT", 1, 1) == 1.0 and ai.walk_speed("ELITE_CHAMPI_WARRIOR", 1, 1) == 1.1
    assert ai.walk_speed("CHAMPION", 1, 1) != 1.1                     # not a Champi


def test_the_barracks_menu_has_the_champi_scout_only_for_four_civilizations():
    assert {r["name"] for r in civs.ROWS if r["name"] not in civs.MISSING["CHAMPI_SCOUT"]} == CIVS
    assert {"AZTECS", "BRITONS"} <= set(civs.MISSING["ELITE_CHAMPI_WARRIOR"])
    server, g = player()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 26:husk_spawn_egg:Champi Scout:50 food · 25 gold · 42 s · queue 0/15" in menus(server)[-1]
    server, g = player("AZTECS", ("FEUDAL_AGE", "CASTLE_AGE"))
    train.open_menu(g, "Steve", BARRACKS)
    assert "Champi" not in menus(server)[-1] and train.queue(g, "Steve", BARRACKS, "CHAMPI_SCOUT") is None


def test_the_upgrades_change_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["c"] = "CHAMPI_SCOUT"
    g.game.entities.setdefault("c", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    g.sites.append({"name": "HOUSE", "player": 1, "footprint": [20, 22, 20, 22], "done": True})   # room for one more unit
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert " 27:book:Champi Runner:90 food · 60 gold · 40 s · research" in menus(server)[-1]
    for old, new, cost, time in (("CHAMPI_SCOUT", "CHAMPI_RUNNER", "90 food · 60 gold", 40),
                                 ("CHAMPI_RUNNER", "CHAMPI_WARRIOR", "150 food · 175 gold", 50),
                                 ("CHAMPI_WARRIOR", "ELITE_CHAMPI_WARRIOR", "650 food · 450 gold", 50)):
        train.open_menu(g, "Steve", BARRACKS)
        assert f" 27:book:{build.pretty(new)}:{cost} · {time} s · research" in menus(server)[-1]
        assert train.order(g, "Steve", rect, 27) == 1
        train.tick(g, time)
        assert g.soldiers["c"] == new and combat.label_command("c", new) in server.log
    train.open_menu(g, "Steve", BARRACKS)
    assert " 26:husk_spawn_egg:Elite Champi Warrior:50 food · 25 gold · 21 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 26) == 1
    uuid, = train.tick(g, 21)
    assert g.soldiers[uuid] == "ELITE_CHAMPI_WARRIOR"
