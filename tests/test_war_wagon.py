"""War Wagon (#1889): the castle of the Koreans trains the War Wagon and researches Elite War Wagon in the Imperial Age,
with the values of game/data/train.jsonl. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup
from test_urumi_swordsman import item, label

from game import combat, train

CASTLE = (12, 4)


def test_the_castle_of_the_koreans_trains_the_war_wagon():
    server, g = setup("KOREANS", food=0, wood=2000, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(g, "WAR_WAGON", f"queue 0/{train.QUEUE}") in menu
    assert f":{label('ELITE_WAR_WAGON_UPGRADE')}:" not in menu       # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.ITEMS["WAR_WAGON"][0]) == 1 and g.queues[rect][0]["name"] == "WAR_WAGON"
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label('WAR_WAGON')}:" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("KOREANS", food=0, wood=2000, gold=2000, ages=3)
    g.soldiers["ww"] = "WAR_WAGON"
    g.game.entities.setdefault("ww", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(g, "ELITE_WAR_WAGON_UPGRADE", "research") in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, "ELITE_WAR_WAGON_UPGRADE")
    train.tick(g, train.seconds(g, "ELITE_WAR_WAGON_UPGRADE"))
    assert "ELITE_WAR_WAGON_UPGRADE" in g.techs and g.soldiers["ww"] == "ELITE_WAR_WAGON"
    assert combat.stats_command("ww", "ELITE_WAR_WAGON") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(g, "ELITE_WAR_WAGON", f"queue 0/{train.QUEUE}") in menu
    assert f":{label('WAR_WAGON')}:" not in menu and f" {train.ITEMS['ELITE_WAR_WAGON_UPGRADE'][0]}:book" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_WAR_WAGON")
    assert train.queue(g, "Steve", CASTLE, "WAR_WAGON") is None
