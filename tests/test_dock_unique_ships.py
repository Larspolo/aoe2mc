"""The unique ships of the dock (#1934): the longship, the turtle ship and the caravel from the Castle Age, only for
their civilizations, and their elite upgrades in the Imperial Age. Fake server, no Minecraft."""
import pytest
from test_dock_train import dock_map
from test_train_menu import menus

from game import civs, combat, fleet, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")
IMPERIAL = CASTLE + ("IMPERIAL_AGE",)
SHIPS = ("CARAVEL", "LONGSHIP", "TURTLE_SHIP")
ALL = sorted(c["name"] for c in civs.ROWS)
CIV = {n: next(c for c in ALL if c not in civs.MISSING.get(n, ())) for n in SHIPS}   # a civilization that has it
NONE = next(c for c in ALL if all(c in civs.MISSING.get(n, ()) for n in SHIPS))      # one with none of them


def dock(civ, ages=IMPERIAL):
    server, g = dock_map(wood=10000)
    g.data["players"]["1"]["civ"] = civ
    g.stock.update(food=10000, gold=10000)
    g.techs.update(ages)
    return server, g


@pytest.mark.parametrize("name", SHIPS)
def test_each_ship_and_its_elite_form_fit_together(name):
    elite, up = f"ELITE_{name}", f"ELITE_{name}_UPGRADE"
    assert train.COSTS[name] == train.COSTS[elite] and train.ITEMS[name][0] == train.ITEMS[elite][0]
    assert fleet.SPEEDS[name] == fleet.SPEEDS[elite] and train.UPGRADES[up] == (name, elite)


@pytest.mark.parametrize("name", SHIPS)
def test_the_dock_of_the_own_civ_shows_the_ship_from_the_castle_age(name):
    label = train.ITEMS[name][2]
    server, g = dock(CIV[name], CASTLE)
    train.open_menu(g, "Steve", (15, 12))
    menu = menus(server)[-1]
    assert f" {train.ITEMS[name][0]}:{train.ITEMS[name][1]}:{label}:" in menu and f"Elite {label}" not in menu
    assert all(train.ITEMS[n][2] + ":" not in menu for n in SHIPS if n != name)   # no ship of another civ
    server, g = dock(NONE, IMPERIAL)
    train.open_menu(g, "Steve", (15, 12))
    assert all(f":{train.ITEMS[n][2]}:" not in menus(server)[-1] for n in SHIPS)
    server, g = dock(CIV[name], ("FEUDAL_AGE",))
    train.open_menu(g, "Steve", (15, 12))
    assert f" {train.ITEMS[name][0]}:{train.ITEMS[name][1]}:{label}:" not in menus(server)[-1]   # the Feudal Age: locked


@pytest.mark.parametrize("name", SHIPS)
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


def test_bogsveigar_gives_the_longships_and_the_archer_line_more_attack():
    for name in ("LONGSHIP", "ELITE_LONGSHIP", "ARBALESTER"):
        s = combat.stats(name)
        assert train.TECHS["BOGSVEIGAR"](name, s).attack > s.attack
    s = combat.stats("CARAVEL")
    assert train.TECHS["BOGSVEIGAR"]("CARAVEL", s) == s
