"""game/train.py: the research time bonuses of the civilizations (#2172, civs.RESEARCH_TIME, AoE2 DE wiki): Achaemenid
stable technologies research 50 % faster, Jurchen siege and fortification technologies 100 % faster, and the Goths
research Loom at once."""
import pytest
from test_age_bonuses import game

from game import train


def test_achaemenid_stable_technologies_take_two_thirds_of_the_time():
    server, g = game("ACHAEMENIDS")
    assert train.seconds(g, "BLOODLINES", "STABLE") == pytest.approx(50 / 1.5, rel=1e-3)
    assert train.seconds(g, "HUSBANDRY", "STABLE") == pytest.approx(40 / 1.5, rel=1e-3)


def test_jurchen_siege_and_fortification_technologies_take_half_the_time():
    server, g = game("JURCHENS")
    assert train.seconds(g, "SIEGE_ENGINEERS", "UNIVERSITY") == 45 / 2
    assert train.seconds(g, "MASONRY", "UNIVERSITY") == 50 / 2


def test_gothic_loom_takes_no_time():
    server, g = game("GOTHS", gold=50)
    assert train.seconds(g, "LOOM", "TOWN_CENTER") == 0
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS["LOOM"][0]) == 1
    train.tick(g, 0.05)                                              # one tick of the game program
    assert "LOOM" in g.techs


def test_other_civilizations_and_technologies_keep_their_time():
    for civ in ("ACHAEMENIDS", "BRITONS", "GOTHS", "JURCHENS"):
        server, g = game(civ)
        assert train.seconds(g, "BLOODLINES", "STABLE") == (50 if civ != "ACHAEMENIDS" else pytest.approx(50 / 1.5, rel=1e-3))
        assert train.seconds(g, "MASONRY", "UNIVERSITY") == (50 if civ != "JURCHENS" else 25), civ
        assert train.seconds(g, "LOOM", "TOWN_CENTER") == (25 if civ != "GOTHS" else 0), civ
        assert train.seconds(g, "WHEELBARROW", "TOWN_CENTER") == 75, civ
