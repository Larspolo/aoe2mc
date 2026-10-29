"""game/train.py: the stable trains the battle elephant in the Castle Age and upgrades it to the elite battle elephant in
the Imperial Age (#1556): only the civilizations of
civs.ELEPHANTS, and no elite upgrade for the Dravidians. A battle elephant is a ravager with a zombie rider."""
from menu_line import item
from test_train_knight import menu, setup

from game import civs, combat, train

STABLE = (11, 3)


def player(civ="KHMER", ages=("FEUDAL_AGE", "CASTLE_AGE")):
    server, g = setup("STABLE", ages)
    g.stock.update(food=10000, gold=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def text(g, name, building=None):
    """The cost and time text of the menu item of name, from the data (as train.show writes it)."""
    return (" · ".join(f"{v} {r}" for r, v in train.price(g, name, building).items()) or "free") + \
        f" · {round(train.seconds(g, name, building), 1):g} s · "


def test_the_stable_menu_has_the_battle_elephant_only_for_its_civilizations():
    for civ in civs.ELEPHANTS:
        server, g = player(civ)
        train.open_menu(g, "Steve", STABLE)
        assert item(menu(server), "Battle Elephant").endswith(":Battle Elephant:" + text(g, "BATTLE_ELEPHANT", "STABLE") +
                                                              "queue 0/15"), civ   # the Malay pay less (civs.COSTS)
    server, g = player("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Elephant" not in menu(server) and train.queue(g, "Steve", STABLE, "BATTLE_ELEPHANT") is None


def test_the_battle_elephant_is_gray_before_the_castle_age():
    server, g = player(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    line = item(menu(server), "Battle Elephant")
    assert ":gray_dye:Battle Elephant:" in line and line.endswith(" Needs the Castle Age")


def test_a_trained_battle_elephant_is_a_ravager_with_a_rider():
    server, g = player()
    rect = train.open_menu(g, "Steve", STABLE)
    assert train.order(g, "Steve", rect, int(item(menu(server), "Battle Elephant").split(":")[0])) == 1
    uuid, = train.tick(g, train.seconds(g, "BATTLE_ELEPHANT", "STABLE"))
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:ravager ") and "minecraft:zombie" in summon
    assert g.soldiers == {uuid: "BATTLE_ELEPHANT"}


def test_the_elite_upgrade_changes_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "BATTLE_ELEPHANT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    rect = train.open_menu(g, "Steve", STABLE)
    up = item(menu(server), "Elite Battle Elephant")
    assert up.endswith(":Elite Battle Elephant:" + text(g, "ELITE_BATTLE_ELEPHANT_UPGRADE", "STABLE") + "research")
    assert train.order(g, "Steve", rect, int(up.split(":")[0])) == 1
    train.tick(g, train.seconds(g, "ELITE_BATTLE_ELEPHANT_UPGRADE", "STABLE"))
    assert "ELITE_BATTLE_ELEPHANT_UPGRADE" in g.techs and g.soldiers["e"] == "ELITE_BATTLE_ELEPHANT"
    assert combat.stats_command("e", "ELITE_BATTLE_ELEPHANT", train.stats(g, "ELITE_BATTLE_ELEPHANT")) in server.log
    assert combat.label_command("e", "ELITE_BATTLE_ELEPHANT") in server.log
    train.open_menu(g, "Steve", STABLE)
    elite = item(menu(server), "Elite Battle Elephant")
    assert elite.endswith(":Elite Battle Elephant:" + text(g, "ELITE_BATTLE_ELEPHANT", "STABLE") + "queue 0/15")
    assert train.order(g, "Steve", rect, int(elite.split(":")[0])) == 1
    uuid, = train.tick(g, train.seconds(g, "ELITE_BATTLE_ELEPHANT", "STABLE"))
    assert g.soldiers[uuid] == "ELITE_BATTLE_ELEPHANT"


def test_the_dravidians_have_no_elite_upgrade():
    server, g = player("DRAVIDIANS", ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    train.open_menu(g, "Steve", STABLE)
    assert item(menu(server), "Battle Elephant") and "Elite Battle Elephant" not in menu(server)
    assert train.queue(g, "Steve", STABLE, "ELITE_BATTLE_ELEPHANT_UPGRADE") is None
