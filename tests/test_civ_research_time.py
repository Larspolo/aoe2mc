"""game/train.py: the research time bonuses of the civilizations (#2172, civs.RESEARCH_TIME, AoE2 DE wiki): Achaemenid
stable technologies, Jurchen siege and fortification technologies and Gothic Loom research faster."""
import pytest
from test_age_bonuses import game

from game import train


FASTER = {"ACHAEMENIDS": (("BLOODLINES", "STABLE"), ("HUSBANDRY", "STABLE")),
          "GOTHS": (("LOOM", "TOWN_CENTER"),),
          "JURCHENS": (("SIEGE_ENGINEERS", "UNIVERSITY"), ("MASONRY", "UNIVERSITY"))}


@pytest.mark.parametrize("civ", sorted(FASTER))
def test_the_technologies_of_the_bonus_take_less_time(civ):
    server, g = game(civ)
    for name, building in FASTER[civ]:
        assert train.seconds(g, name, building) < train.TRAIN_TIMES[name], name


def test_gothic_loom_is_done_after_its_time():
    server, g = game("GOTHS", gold=50)
    rect = train.open_menu(g, "Steve", (3, 3))
    assert train.order(g, "Steve", rect, train.ITEMS["LOOM"][0]) == 1
    train.tick(g, train.seconds(g, "LOOM", "TOWN_CENTER") + 0.05)   # and one tick of the game program
    assert "LOOM" in g.techs


def test_other_civilizations_and_technologies_keep_their_time():
    for civ in ("ACHAEMENIDS", "BRITONS", "GOTHS", "JURCHENS"):
        server, g = game(civ)
        for other, items in FASTER.items():
            for name, building in items * (other != civ):
                assert train.seconds(g, name, building) == train.TRAIN_TIMES[name], (civ, name)
        assert train.seconds(g, "WHEELBARROW", "TOWN_CENTER") == train.TRAIN_TIMES["WHEELBARROW"], civ
