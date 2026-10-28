"""game/civs.py: Shu land siege units and Lou Chuans move 10 % faster in the Castle Age and 15 % in the Imperial Age,
as in AoE2 DE (wiki "Shu", civilization bonuses, #2179). The key "units" of the Shu line of data/civs.jsonl."""
import pytest
from test_bloodlines import setup
from test_trade_cog import docks_map

from game import civs, fleet, train


def player(g, civ, *ages):
    g.data.setdefault("players", {}).setdefault("1", {})["civ"] = civ
    g.techs.update(ages)
    return g


def test_shu_siege_and_lou_chuans_are_faster_in_the_castle_and_imperial_age():
    for ages, f in (((), 1.0), (("CASTLE_AGE",), 1.1), (("CASTLE_AGE", "IMPERIAL_AGE"), 1.15)):
        g = player(setup()[1], "SHU", *ages)
        for name in ("MANGONEL", "BATTERING_RAM", "SCORPION", "TREBUCHET"):
            assert train.speed(g, name) == pytest.approx(f), (ages, name)
        g = player(docks_map()[1], "SHU", *ages)
        assert fleet.speed("LOU_CHUAN", 1, g) == pytest.approx(fleet.speed("LOU_CHUAN", 1) * f), ages


def test_other_units_and_other_civilizations_do_not_change():
    g = player(setup()[1], "SHU", "CASTLE_AGE", "IMPERIAL_AGE")
    assert civs.speed(g, "MAN_AT_ARMS") == 1 and civs.speed(g, "KNIGHT") == 1 and civs.speed(g, "GALLEY") == 1
    g = player(setup()[1], "CHINESE", "CASTLE_AGE", "IMPERIAL_AGE")
    assert civs.speed(g, "MANGONEL") == 1 and civs.speed(g, "LOU_CHUAN") == 1
