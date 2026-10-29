"""game/train.py: the siege workshop trains the flaming camel in the Imperial Age (#2190), only for the civilizations
that have it."""
from test_bombard_cannon import setup
from test_loom import menus

from game import civs, train

NAME = "FLAMING_CAMEL"
WITH = sorted(set(c["name"] for c in civs.ROWS) - set(civs.MISSING[NAME]))[0]
WITHOUT = sorted(civs.MISSING[NAME])[0]


def menu(civ):
    server, g = setup()
    g.stock["food"] = 1000
    g.data["players"] = {"1": {"civ": civ}}
    train.open_menu(g, "Steve", (3, 3))
    return server, g, menus(server)[-1]


def test_a_civilization_with_it_sees_it():
    server, g, text = menu(WITH)
    (slot, icon, label), cost = train.ITEMS[NAME], train.COSTS[NAME]
    price = " · ".join(f"{v} {k}" for k, v in cost.items())
    assert f"{slot}:{icon}:{label}:{price} · {train.seconds(g, NAME):g} s · queue 0/15" in text
    assert train.queue(g, "Steve", (3, 3), NAME)
    assert g.stock["food"] == 1000 - cost.get("food", 0) and g.stock["gold"] == 1000 - cost.get("gold", 0)


def test_a_civilization_without_it_does_not_see_it():
    server, g, text = menu(WITHOUT)
    assert train.ITEMS[NAME][2] not in text
    assert not train.queue(g, "Steve", (3, 3), NAME) and g.stock["food"] == 1000
