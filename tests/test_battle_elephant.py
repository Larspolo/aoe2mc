"""game/train.py: the stable trains the battle elephant in the Castle Age and upgrades it to the elite battle elephant in
the Imperial Age (#1556, AoE2 DE wiki infoboxes "Battle Elephant", "Elite Battle Elephant"): only the civilizations of
civs.ELEPHANTS, and no elite upgrade for the Dravidians. A battle elephant is a ravager with a zombie rider."""
import re

from test_train_knight import menu, setup

from game import build, civs, combat, train

STABLE = (11, 3)


def player(civ="KHMER", ages=("FEUDAL_AGE", "CASTLE_AGE")):
    server, g = setup("STABLE", ages)
    g.stock.update(food=10000, gold=10000)
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return server, g


def test_the_values_are_those_of_the_wiki():
    for name in ("BATTLE_ELEPHANT", "ELITE_BATTLE_ELEPHANT"):
        assert len(train.HELP[name]) <= 50
    assert [build.AGE[n] for n in ("BATTLE_ELEPHANT", "ELITE_BATTLE_ELEPHANT")] == [2, 3]


def test_the_stable_menu_has_the_battle_elephant_only_for_its_civilizations():
    assert set(civs.ELEPHANTS) == {"BENGALIS", "BURMESE", "DRAVIDIANS", "KHMER", "MALAY", "VIETNAMESE"}
    for civ in civs.ELEPHANTS:
        server, g = player(civ)
        train.open_menu(g, "Steve", STABLE)
        assert " 7:ravager_spawn_egg:Battle Elephant:" in menu(server)   # the Malay pay less (civs.COSTS)
    server, g = player("KHMER")
    train.open_menu(g, "Steve", STABLE)
    assert " 7:ravager_spawn_egg:Battle Elephant:100 food · 70 gold · 24 s · queue 0/15" in menu(server)
    server, g = player("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Elephant" not in menu(server) and train.queue(g, "Steve", STABLE, "BATTLE_ELEPHANT") is None


def test_the_battle_elephant_is_gray_before_the_castle_age():
    server, g = player(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    assert re.search("7:gray_dye:Battle Elephant:[^ ]* .* Needs the Castle Age", menu(server))


def test_a_trained_battle_elephant_is_a_ravager_with_a_rider():
    server, g = player()
    assert train.order(g, "Steve", train.open_menu(g, "Steve", STABLE), 7) == 1
    uuid, = train.tick(g, 24)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert summon.startswith("summon minecraft:ravager ") and "minecraft:zombie" in summon
    assert g.soldiers == {uuid: "BATTLE_ELEPHANT"}


def test_the_elite_upgrade_changes_the_live_and_the_new_units():
    server, g = player(ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    g.soldiers["e"] = "BATTLE_ELEPHANT"
    g.game.entities.setdefault("e", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    rect = train.open_menu(g, "Steve", STABLE)
    assert f" {train.MORE + 1}:book:Elite Battle Elephant:1100 food · 700 gold · 100 s · research" in menu(server)
    assert train.order(g, "Steve", rect, train.MORE + 1) == 1
    train.tick(g, 100)
    assert "ELITE_BATTLE_ELEPHANT_UPGRADE" in g.techs and g.soldiers["e"] == "ELITE_BATTLE_ELEPHANT"
    assert combat.stats_command("e", "ELITE_BATTLE_ELEPHANT", train.stats(g, "ELITE_BATTLE_ELEPHANT")) in server.log
    assert combat.label_command("e", "ELITE_BATTLE_ELEPHANT") in server.log
    train.open_menu(g, "Steve", STABLE)
    assert " 7:ravager_spawn_egg:Elite Battle Elephant:100 food · 70 gold · 24 s · queue 0/15" in menu(server)
    assert train.order(g, "Steve", rect, 7) == 1
    uuid, = train.tick(g, 24)
    assert g.soldiers[uuid] == "ELITE_BATTLE_ELEPHANT"


def test_the_dravidians_have_no_elite_upgrade():
    server, g = player("DRAVIDIANS", ages=("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"))
    train.open_menu(g, "Steve", STABLE)
    assert "Battle Elephant:100 food" in menu(server) and "Elite Battle Elephant" not in menu(server)
    assert train.queue(g, "Steve", STABLE, "ELITE_BATTLE_ELEPHANT_UPGRADE") is None
