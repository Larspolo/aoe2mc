"""The unique ships of the dock (#1934): the longship (Danes, Saxons, Varangians, Vikings), the turtle ship (Koreans)
and the caravel (Portuguese) from the Castle Age, and their elite upgrades in the Imperial Age, with the base values of
the AoE2 DE wiki infoboxes (the civilization bonuses are epic #1088). Fake server, no Minecraft."""
import pytest
from test_dock_train import dock_map
from test_train_menu import menus

from game import civs, combat, fleet, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
# name: (civilizations, cost, time, hit points, slot; elite cost, elite time, elite hit points)
SHIPS = {"LONGSHIP": ({"DANES", "SAXONS", "VARANGIANS", "VIKINGS"}, {"wood": 100, "gold": 50}, 25, 125, 22,
                      {"food": 750, "gold": 475}, 60, 130),
         "TURTLE_SHIP": ({"KOREANS"}, {"wood": 190, "gold": 130}, 50, 260, 24, {"food": 650, "gold": 500}, 65, 350),
         "CARAVEL": ({"PORTUGUESE"}, {"wood": 90, "gold": 43}, 25, 130, 27, {"food": 700, "gold": 525}, 60, 150)}
CIV = {"LONGSHIP": "VIKINGS", "TURTLE_SHIP": "KOREANS", "CARAVEL": "PORTUGUESE"}


def dock(civ, ages=IMPERIAL):
    server, g = dock_map(wood=10000)
    g.data["players"]["1"]["civ"] = civ
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    return server, g


@pytest.mark.parametrize("name", sorted(SHIPS))
def test_each_ship_has_the_wiki_values(name):
    own, cost, time, hp, slot, up_cost, up_time, elite_hp = SHIPS[name]
    elite, up = f"ELITE_{name}", f"ELITE_{name}_UPGRADE"
    assert train.COSTS[name] == train.COSTS[elite] == cost and train.TRAIN_TIMES[name] == time
    assert train.COSTS[up] == up_cost and train.TRAIN_TIMES[up] == up_time
    assert combat.stats(name).hp == hp and combat.stats(elite).hp == elite_hp
    assert combat.SHIP in combat.stats(name).classes and combat.WAR in combat.stats(elite).classes
    assert train.ITEMS[name][0] == train.ITEMS[elite][0] == slot and train.ITEMS[up][0] == slot + 1
    assert fleet.SPEEDS[name] == fleet.SPEEDS[elite]
    assert train.UPGRADES[up] == (name, elite)
    for n in (name, elite, up):
        assert not own & set(civs.MISSING[n]) and "FRANKS" in civs.MISSING[n]


@pytest.mark.parametrize("name", sorted(SHIPS))
def test_the_dock_of_the_own_civ_shows_the_ship_from_the_castle_age(name):
    label = train.ITEMS[name][2]
    server, g = dock(CIV[name], CASTLE)
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert f" {SHIPS[name][4]}:{train.ITEMS[name][1]}:{label}:" in menu and f"Elite {label}" not in menu
    assert all(train.ITEMS[n][2] + ":" not in menu for n in SHIPS if n != name)   # no ship of another civ
    server, g = dock("FRANKS", IMPERIAL)
    train.open_menu(g, "Steve", (15, 12))
    assert all(f":{train.ITEMS[n][2]}:" not in menus(server)[-1] for n in SHIPS)
    server, g = dock(CIV[name], ("FEUDAL_AGE",))
    train.open_menu(g, "Steve", (15, 12))
    assert f" {SHIPS[name][4]}:{train.ITEMS[name][1]}:{label}:" not in menus(server)[-1]   # the Feudal Age: locked


@pytest.mark.parametrize("name", sorted(SHIPS))
def test_the_elite_upgrade_turns_the_own_ships_into_the_elite_form(name):
    server, g = dock(CIV[name])
    g.soldiers["s"] = name
    g.game.entities.setdefault("s", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    up = f"ELITE_{name}_UPGRADE"
    assert train.queue(g, "Steve", (15, 12), up)
    train.tick(g, train.TRAIN_TIMES[up])
    assert up in g.techs and g.soldiers["s"] == f"ELITE_{name}"
    assert combat.stats_command("s", f"ELITE_{name}", train.stats(g, f"ELITE_{name}")) in server.log   # with the civ bonuses
    assert train.queue(g, "Steve", (15, 12), f"ELITE_{name}") and train.queue(g, "Steve", (15, 12), name) is None


def test_bogsveigar_gives_the_longships_and_the_archer_line_1_attack():
    assert train.forms("ARCHER") == ("ARCHER", "CROSSBOWMAN", "ARBALESTER")
    for name in ("LONGSHIP", "ELITE_LONGSHIP", "ARBALESTER"):
        s = combat.stats(name)
        assert train.TECHS["BOGSVEIGAR"](name, s).attack == s.attack + 1
    s = combat.stats("CARAVEL")
    assert train.TECHS["BOGSVEIGAR"]("CARAVEL", s) == s
