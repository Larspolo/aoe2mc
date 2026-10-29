"""The AoE2 lobby setting "Full Tech Tree" of the game program (#2354, epic #2263): `game/run.py --play
--full-tech-tree` gives each civilization the full tech tree and its unique units, but no civilization and team
bonuses and no unique technologies or buildings. AoE2 wiki "Full Tech Tree"."""
import pytest
from test_castle_upgrades import STABLE, setup
from test_forging import menus

from game import combat, run, train

civs = train.civs                                    # with the unique units of train.own_civ_only (#1760)

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def game(civ="AZTECS", full=True, ally=None):
    server, g = setup(ages=CASTLE, techs=())
    g.data["players"] = {"1": {"civ": civ}} | ({"2": {"civ": ally}} if ally else {})
    if full:
        g.data["full_tech_tree"] = True
    return server, g


def test_the_aztecs_train_the_knight():
    server, g = game()
    assert not civs.missing(g, "KNIGHT") and not civs.missing(g, "HUSBANDRY")
    train.open_menu(g, "Steve", STABLE)
    assert "Knight" in menus(server)[-1]
    assert train.queue(g, "Steve", STABLE, "KNIGHT")


def test_the_britons_keep_only_the_longbowman_at_the_castle():
    _, g = game("BRITONS")
    castle = train.trains(g, "CASTLE")
    assert "LONGBOWMAN" in castle and "MANGUDAI" not in castle
    assert not any(t in castle for t, c in train.BY_KEY["civ"].items())            # no unique technologies
    assert civs.missing(g, "JAGUAR_WARRIOR") and not civs.missing(g, "LONGBOWMAN")


def test_regional_units_come_with_the_exceptions():
    _, g = game("BRITONS")
    assert not civs.missing(g, "BATTLE_ELEPHANT") and not civs.missing(g, "STEPPE_LANCER")    # regional units
    assert civs.missing(g, "FIRE_LANCER") and civs.missing(g, "CHAMPI_SCOUT") and civs.missing(g, "MULE_CART")
    assert civs.missing(g, "CAMEL_SCOUT")                                       # the scout of the Gurjaras
    assert not civs.missing(game("CHINESE")[1], "FIRE_LANCER")                  # its own civilizations keep it


def test_no_civilization_has_the_xolotl_warrior_and_the_unique_buildings():
    for civ in sorted({r["name"] for r in civs.ROWS}):
        _, g = game(civ)
        assert civs.missing(g, "XOLOTL_WARRIOR") and civs.missing(g, "FORTIFIED_CHURCH"), civ
        assert civs.missing(g, "KREPOST") and civs.missing(g, "GENITOUR"), civ


def test_the_armenians_keep_the_mule_cart_and_lack_the_camps():
    _, g = game("ARMENIANS")
    assert not civs.missing(g, "MULE_CART") and civs.missing(g, "LUMBER_CAMP") and civs.missing(g, "MINING_CAMP")
    assert not civs.missing(game("POLES")[1], "MILL")                          # the Poles lose the Folwark


def test_the_civilization_bonuses_go():
    base = {"food": 200, "wood": 200, "gold": 100, "stone": 200}
    assert civs.start(game("CHINESE", full=False)[1], base) != base
    assert civs.start(game("CHINESE")[1], base) == base
    base = combat.stats("KNIGHT").hp
    assert train.stats(game("FRANKS", full=False)[1], "KNIGHT").hp > base           # the Frankish cavalry bonus
    franks, goths = train.stats(game("FRANKS")[1], "KNIGHT"), train.stats(game("GOTHS")[1], "KNIGHT")
    assert franks.hp == goths.hp == base


def test_the_team_bonuses_go():
    _, g = game("BRITONS", full=False, ally="SAXONS")
    g.data["players"]["1"]["team"] = g.data["players"]["2"]["team"] = 1
    assert civs.repair_rate(g) > 1
    g.data["full_tech_tree"] = True
    assert civs.repair_rate(g) == 1


def test_without_the_setting_the_game_stays():
    server, g = game(full=False)
    assert civs.missing(g, "KNIGHT") and not civs.missing(g, "XOLOTL_WARRIOR")
    assert "ATLATL" in train.trains(g, "CASTLE")


def test_run_offers_the_setting(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "--full-tech-tree" in capsys.readouterr().out


def test_the_bonuses_of_the_world_data_go():
    data = {"level_height": 2, "players": {"1": {"civ": "GEORGIANS"}, "2": {"civ": "FRANKS"}}}
    assert combat.elevation_command(data).split()[3][3:] != combat.elevation_command(data).split()[4][3:]
    data["full_tech_tree"] = True
    assert combat.elevation_command(data).split()[3][3:] == combat.elevation_command(data).split()[4][3:]
