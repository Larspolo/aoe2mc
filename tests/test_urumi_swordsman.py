"""Urumi Swordsman (#1754): the castle of the Dravidians trains the urumi swordsman and researches Elite Urumi Swordsman
in the Imperial Age, with the values of game/data/train.jsonl. The upgrade changes the live and the new units."""
from test_train_castle import menus, setup

from game import combat, train

CASTLE = (12, 4)
UNIT, ELITE, UPGRADE = "URUMI_SWORDSMAN", "ELITE_URUMI_SWORDSMAN", "ELITE_URUMI_SWORDSMAN_UPGRADE"


def item(g, name, state):
    """The menu text of name: slot, item, name, cost, time and state."""
    slot, kind, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, name).items())
    return f" {slot}:{kind}:{label}:{cost} · {round(train.seconds(g, name), 1):g} s · {state} "


def label(name):
    return train.ITEMS[name][2]


def test_the_castle_of_the_dravidians_trains_the_urumi_swordsman():
    server, g = setup("DRAVIDIANS", food=2000, wood=0, gold=2000)
    rect = train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(g, UNIT, f"queue 0/{train.QUEUE}") in menu
    assert f":{label(UPGRADE)}:" not in menu                                  # the upgrade: the Imperial Age
    assert train.order(g, "Steve", rect, train.ITEMS[UNIT][0]) == 1 and g.queues[rect][0]["name"] == UNIT
    server, g = setup("BRITONS", ages=3)
    train.open_menu(g, "Steve", CASTLE)
    assert f":{label(UNIT)}:" not in menus(server)[-1]


def test_the_upgrade_changes_the_live_and_the_new_units():
    server, g = setup("DRAVIDIANS", food=2000, wood=0, gold=2000, ages=3)
    g.soldiers["ct"] = "URUMI_SWORDSMAN"
    g.game.entities.setdefault("ct", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    train.open_menu(g, "Steve", CASTLE)
    assert item(g, UPGRADE, "research") in menus(server)[-1] + " "
    assert train.queue(g, "Steve", CASTLE, UPGRADE)
    train.tick(g, train.seconds(g, UPGRADE))
    assert "ELITE_URUMI_SWORDSMAN_UPGRADE" in g.techs and g.soldiers["ct"] == "ELITE_URUMI_SWORDSMAN"
    assert combat.stats_command("ct", "ELITE_URUMI_SWORDSMAN") in server.log
    train.open_menu(g, "Steve", CASTLE)
    menu = menus(server)[-1] + " "
    assert item(g, ELITE, f"queue 0/{train.QUEUE}") in menu
    assert f":{label(UNIT)}:" not in menu and f" {train.ITEMS[UPGRADE][0]}:{train.ITEMS[UPGRADE][1]}:" not in menu
    assert train.queue(g, "Steve", CASTLE, "ELITE_URUMI_SWORDSMAN")
    assert train.queue(g, "Steve", CASTLE, "URUMI_SWORDSMAN") is None
