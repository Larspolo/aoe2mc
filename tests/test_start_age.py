"""The AoE2 DE setting "Starting age" of the game program (#2265, epic #2263): `game/run.py --play --age AGE` starts
each player in the age, with the technologies of all earlier ages (AoE2 wiki "Random map"); "post-imperial" with all
technologies except Spies (wiki "Post-Imperial Age"). The start resources stay those of the setting "Starting
resources": the wiki gives no other values for a later age, and an age bonus pays only when a player advances."""
import pytest
from test_gather import FakeServer, grid

from game import gather, run, train


def player(civ=None, age=None):
    data = grid([[64] * 8 for _ in range(8)], [])
    if civ:
        data["players"] = {"1": {"civ": civ}}
    g = gather.Gather(FakeServer({}), data)
    if age:
        train.start(g, age)
    return g


def test_dark_is_the_start_of_today():
    g = player(age="dark")
    assert g.techs == set() and train.age(g) == "Dark Age" and g.stock == player().stock


def test_castle_has_the_techs_of_the_dark_and_feudal_age():
    g = player(age="castle")
    assert train.age(g) == "Castle Age" and {"FEUDAL_AGE", "CASTLE_AGE"} <= g.techs and "IMPERIAL_AGE" not in g.techs
    assert {"LOOM", "DOUBLE_BIT_AXE", "HORSE_COLLAR"} <= g.techs   # Dark Age and Feudal Age technologies
    assert "BOW_SAW" not in g.techs and train.unlocked(g, "BOW_SAW")   # the menu offers the Castle Age items
    assert not train.unlocked(g, "TWO_MAN_SAW")


def test_the_sidebar_names_the_start_age():
    g = player(age="castle")
    train.sidebar(g)
    assert any("Resources (Castle Age)" in c for c in g.game.log)


def test_a_later_age_keeps_the_start_resources():
    for civ in (None, "DRAVIDIANS", "ETHIOPIANS", "SPANISH"):   # no age gift, no gold for a technology
        assert player(civ, "imperial").stock == player(civ).stock == player(civ, "dark").stock, civ
    assert player(age="castle").stock == gather.START


def test_post_imperial_has_all_techs_but_spies():
    g = player(age="post-imperial")
    assert train.age(g) == "Imperial Age" and {"TWO_MAN_SAW", "BOW_SAW", "IMPERIAL_AGE"} <= g.techs
    assert "SPIES" not in g.techs and "TWO_MAN_SAW" not in player(age="imperial").techs


def test_a_civilization_gets_only_its_own_techs():
    for t in player("FRANKS", "post-imperial").techs:
        assert not train.civs.missing(player("FRANKS"), t), t


def test_run_offers_each_age(capsys):
    with pytest.raises(SystemExit):
        run.main(["--help"])
    assert "--age {" + ",".join(train.STARTS) + "}" in capsys.readouterr().out


def test_the_start_units_get_the_upgrades_of_the_earlier_ages():
    data = grid([[64] * 8 for _ in range(8)], [])
    data["objects"].append({"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "u1", "x": 1, "y": 1})
    g = gather.Gather(FakeServer({}), data)
    train.start(g, "imperial")                                     # Man-at-Arms (Feudal), Long Swordsman (Castle)
    assert g.soldiers == {"u1": "LONG_SWORDSMAN"}
