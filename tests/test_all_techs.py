"""The AoE2 "All Techs" setting of the game program (#2298, epic #2263): `game/run.py --play --all-techs` gives each
civilization the generic units and technologies that its tech tree does not have (the key "not_civs"
of their lines in game/data/train.jsonl and build.jsonl, #3200). AoE2 wiki "Full Tech Tree", section "All Techs": the whole tech tree, and the civilization and
team bonuses stay. The unique units and technologies stay with their civilization."""
import pytest
from test_castle_upgrades import STABLE, setup
from test_forging import menus

from game import run, train

civs = train.civs                                    # with the unique units of train.own_civ_only (#1760)

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def stable(civ="AZTECS", all_techs=False):
    server, g = setup(ages=CASTLE, techs=())
    g.data["players"] = {"1": {"civ": civ}}
    if all_techs:
        g.data["all_techs"] = True
    return server, g


def test_a_civilization_gets_the_items_of_its_missing_list():
    server, g = stable(all_techs=True)
    assert not civs.missing(g, "KNIGHT") and not civs.missing(g, "HUSBANDRY")
    train.open_menu(g, "Steve", STABLE)
    assert "Knight" in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "KNIGHT")


def test_the_unique_units_stay_with_their_civilization():
    server, g = stable("BRITONS", all_techs=True)
    assert "LONGBOWMAN" in train.trains(g, "CASTLE") and "MANGUDAI" not in train.trains(g, "CASTLE")
    assert civs.missing(g, "JAGUAR_WARRIOR") and civs.missing(g, "ELITE_JAGUAR_WARRIOR_UPGRADE")
    assert train.BY_KEY["civ"]["ATLATL"] != "BRITONS" and civs.missing(g, "ATLATL")   # a unique technology


def test_without_the_setting_the_tech_tree_stays():
    server, g = stable()
    assert civs.missing(g, "KNIGHT")
    train.open_menu(g, "Steve", STABLE)
    assert "Knight" not in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "KNIGHT") is None


def test_run_offers_the_setting(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "--all-techs" in capsys.readouterr().out
