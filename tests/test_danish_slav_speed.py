"""game/civs.py: Danish Varangian Guards and Longships move 10 % faster, Slav monks 20 % faster, as in AoE2 DE (wiki
"Danes" and "Slavs", civilization bonuses, #2245). The key "units" of the civilization lines of data/civs.jsonl."""
import pytest
from test_bloodlines import setup
from test_trade_cog import docks_map

from game import civs, fleet, train


def player(g, civ):
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    return g


def test_danish_varangian_guards_and_longships_move_10_percent_faster():
    g = player(setup()[1], "DANES")
    for name in ("VARANGIAN_GUARD", "ELITE_VARANGIAN_GUARD"):
        assert train.speed(g, name) == pytest.approx(1.1), name
    g = player(docks_map()[1], "DANES")
    for name in ("LONGSHIP", "ELITE_LONGSHIP"):
        assert fleet.speed(name, 1, g) == pytest.approx(fleet.speed(name, 1) * 1.1), name
    assert fleet.speed("GALLEY", 1, g) == fleet.speed("GALLEY", 1)


def test_slav_monks_move_20_percent_faster():
    assert civs.speed(player(setup()[1], "SLAVS"), "MONK") == pytest.approx(1.2)


def test_other_units_and_other_civilizations_do_not_change():
    g = player(setup()[1], "DANES")
    assert civs.speed(g, "MAN_AT_ARMS") == 1 and civs.speed(g, "MONK") == 1
    assert civs.speed(player(setup()[1], "SLAVS"), "VARANGIAN_GUARD") == 1
    g = player(setup()[1], "VIKINGS")
    assert civs.speed(g, "VARANGIAN_GUARD") == 1 and civs.speed(g, "LONGSHIP") == 1 and civs.speed(g, "MONK") == 1
