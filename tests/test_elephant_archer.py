"""game/train.py: the archery range trains the elephant archer in the Castle Age and upgrades it to the elite elephant
archer in the Imperial Age (#1952, AoE2 DE wiki infoboxes "Elephant Archer (Age of Empires II)" revision 1091781,
"Elite Elephant Archer" revision 1091782): only the Bengalis, Dravidians and Gurjaras. It is a ravager with a skeleton
archer rider (units.classify)."""
from test_train_knight import menu, setup

from game import build, civs, combat, train

RANGE = (11, 3)
UNIT, UPGRADE = 21, 22                                                 # the row under the queue row (train.MORE + 3, + 4)


def player(civ="BENGALIS", ages=("FEUDAL_AGE", "CASTLE_AGE")):
    server, g = setup("ARCHERY_RANGE", ages)
    g.stock.update(food=10000, gold=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_values_are_those_of_the_wiki():
    for name in ("ELEPHANT_ARCHER", "ELITE_ELEPHANT_ARCHER"):
        assert len(train.HELP[name]) <= 50
    assert [build.AGE[n] for n in ("ELEPHANT_ARCHER", "ELITE_ELEPHANT_ARCHER")] == [2, 3]
    assert (train.ITEMS["ELEPHANT_ARCHER"][0], train.ITEMS["ELITE_ELEPHANT_ARCHER_UPGRADE"][0]) == (UNIT, UPGRADE)


def test_only_the_bengalis_dravidians_and_gurjaras_train_it():
    for civ in ("BENGALIS", "DRAVIDIANS", "GURJARAS"):
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert f" {UNIT}:ravager_spawn_egg:Elephant Archer:" in menu(server), civ
    for civ in ("FRANKS", "HINDUSTANIS"):
        server, g = player(civ)
        train.open_menu(g, "Steve", RANGE)
        assert "Elephant" not in menu(server) and train.queue(g, "Steve", RANGE, "ELEPHANT_ARCHER") is None, civ


def test_a_trained_elephant_archer_is_a_ravager_with_an_archer_rider():
    server, g = player()
    train.open_menu(g, "Steve", RANGE)
    assert f" {UNIT}:ravager_spawn_egg:Elephant Archer:70 food · 80 gold · 32 s · queue 0/15" in menu(server)
    assert train.order(g, "Steve", train.open_menu(g, "Steve", RANGE), UNIT) == 1
    uuid, = train.tick(g, 32)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:ravager ") and "minecraft:skeleton" in summon and "minecraft:bow" in summon
    assert g.soldiers == {uuid: "ELEPHANT_ARCHER"}


def test_the_elite_upgrade_changes_the_live_and_the_new_units():
    server, g = player("GURJARAS", ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "ELEPHANT_ARCHER"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    rect = train.open_menu(g, "Steve", RANGE)
    assert f" {UPGRADE}:book:Elite Elephant Archer:900 food · 500 gold · 80 s · research" in menu(server)
    assert train.order(g, "Steve", rect, UPGRADE) == 1
    train.tick(g, 80)
    assert "ELITE_ELEPHANT_ARCHER_UPGRADE" in g.techs and g.soldiers["e"] == "ELITE_ELEPHANT_ARCHER"
    assert combat.stats_command("e", "ELITE_ELEPHANT_ARCHER", train.stats(g, "ELITE_ELEPHANT_ARCHER")) in server.log
    train.open_menu(g, "Steve", RANGE)
    assert f" {UNIT}:ravager_spawn_egg:Elite Elephant Archer:70 food · 80 gold · 32 s" in menu(server)
    assert train.order(g, "Steve", rect, UNIT) == 1
    uuid, = train.tick(g, 32)
    assert g.soldiers[uuid] == "ELITE_ELEPHANT_ARCHER"


def test_the_civilizations_of_the_wiki():
    have = set().union(*civs.MISSING.values()) - set(civs.MISSING["ELEPHANT_ARCHER"])
    assert have == {"BENGALIS", "DRAVIDIANS", "GURJARAS"}
