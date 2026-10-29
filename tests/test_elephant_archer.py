"""game/train.py: the archery range trains the elephant archer in the Castle Age and upgrades it to the elite elephant
archer in the Imperial Age (#1952), for the civilizations that have it. It is a ravager with a skeleton archer rider
(units.classify)."""
from test_train_knight import menu, setup

from game import combat, train

RANGE = (11, 3)
UNIT, UPGRADE = train.ITEMS["ELEPHANT_ARCHER"][0], train.ITEMS["ELITE_ELEPHANT_ARCHER_UPGRADE"][0]


def entry(g, name, state):
    """The menu item of name with its cost and time for the player of g."""
    slot, icon, label = train.ITEMS[name]
    cost = " · ".join(f"{v} {k}" for k, v in train.COSTS[name].items())
    return f" {slot}:{icon}:{label}:{cost} · {train.seconds(g, name):g} s · {state}"


def player(civ="BENGALIS", ages=("FEUDAL_AGE", "CASTLE_AGE")):
    server, g = setup("ARCHERY_RANGE", ages)
    g.stock.update(food=10000, gold=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_a_trained_elephant_archer_is_a_ravager_with_an_archer_rider():
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert entry(g, "ELEPHANT_ARCHER", "queue 0/15") in menu(server)
    assert train.order(g, "Steve", train.open_menu(g, "Steve", RANGE), UNIT) == 1
    uuid, = train.tick(g, train.seconds(g, "ELEPHANT_ARCHER"))
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:ravager ") and "minecraft:skeleton" in summon and "minecraft:bow" in summon
    assert g.soldiers == {uuid: "ELEPHANT_ARCHER"}


def test_the_elite_upgrade_changes_the_live_and_the_new_units():
    server, g = player("GURJARAS", ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "ELEPHANT_ARCHER"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    rect = train.open_menu(g, "Steve", RANGE)
    assert entry(g, "ELITE_ELEPHANT_ARCHER_UPGRADE", "research") in menu(server)
    assert train.order(g, "Steve", rect, UPGRADE) == 1
    train.tick(g, train.TRAIN_TIMES["ELITE_ELEPHANT_ARCHER_UPGRADE"])
    assert "ELITE_ELEPHANT_ARCHER_UPGRADE" in g.techs and g.soldiers["e"] == "ELITE_ELEPHANT_ARCHER"
    assert combat.stats_command("e", "ELITE_ELEPHANT_ARCHER", train.stats(g, "ELITE_ELEPHANT_ARCHER")) in server.log
    train.open_menu(g, "Steve", RANGE)
    assert entry(g, "ELITE_ELEPHANT_ARCHER", "queue 0/15") in menu(server)
    assert train.order(g, "Steve", rect, UNIT) == 1
    uuid, = train.tick(g, train.seconds(g, "ELITE_ELEPHANT_ARCHER"))
    assert g.soldiers[uuid] == "ELITE_ELEPHANT_ARCHER"

