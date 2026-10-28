"""The civilization bonus switches under the AoE2 lobby setting "Full Tech Tree" (#3095, #2354): the Athenian policies,
the Macedonian Recruitment Doctrines and the Achaemenid town center upgrades are "none" there, as in AoE2 (AoE2 wiki
"Full Tech Tree": the setting removes the civilization bonuses). A switch with no doctrine changes nothing. Fake server
of test_recruitment_doctrines."""
import pytest
from test_forging import menus
from test_recruitment_doctrines import game, rect

from game import civs, train

NINE = ("ECONOMIC_POLICY", "MILITARY_POLICY", "NAVAL_POLICY", "BARRACKS_RECRUITMENT_DOCTRINE",
        "ARCHERY_RANGE_RECRUITMENT_DOCTRINE", "STABLE_RECRUITMENT_DOCTRINE", "ECONOMIC_TOWN_CENTER",
        "MILITARY_TOWN_CENTER", "DEFENSIVE_TOWN_CENTER")


@pytest.mark.parametrize("civ", [r["name"] for r in civs.ROWS])
def test_full_tech_tree_removes_the_civilization_bonus_switches(civ):
    _, g = game(civ)
    g.data["full_tech_tree"] = True
    assert all(civs.missing(g, name) for name in NINE)


def test_full_tech_tree_shows_no_doctrine_at_the_barracks():
    server, g = game("MACEDONIANS")
    g.data["full_tech_tree"] = True
    train.show(g, "Steve", rect("BARRACKS"))
    assert "Recruitment Doctrine" not in " ".join(menus(server))


def test_a_switch_with_no_doctrine_changes_nothing():
    _, g = game("ATHENIANS")
    g.data["full_tech_tree"] = True
    train.switch(g, "Steve", "BARRACKS")
    assert train.doctrine(g, "BARRACKS")[0] == "Balanced" and not vars(g).get("doctrines")


def test_without_full_tech_tree_a_macedonian_keeps_the_doctrine():
    _, g = game("MACEDONIANS")
    assert not civs.missing(g, "BARRACKS_RECRUITMENT_DOCTRINE")
    train.switch(g, "Steve", "BARRACKS")
    assert train.doctrine(g, "BARRACKS")[0] != "Balanced"
