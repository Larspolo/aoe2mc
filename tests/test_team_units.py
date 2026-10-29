"""Shared units of the AoE2 team bonuses (#1619): a player also gets the Genitour (Berbers) and the Imperial Skirmisher
upgrade (Vietnamese, not for the Turks) when an allied player (the same `team` of aoe2mc.json) has the civilization,
as on the AoE2 DE wiki ("Team bonus"). An enemy of that civilization gives nothing."""
from test_castle_upgrades import RANGE, research, setup
from test_forging import menus

from game import civs, train

IMPERIAL = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")


def game(civ, other, team=1, other_team=1):
    server, g = setup(ages=IMPERIAL, techs=())
    g.data["players"] = {"0": {"civ": "GAIA", "team": None}, "1": {"civ": civ, "team": team},
                         "2": {"civ": other, "team": other_team}}
    return server, g


def range_menu(server, g):
    train.open_menu(g, "Steve", RANGE)
    return menus(server)[-1]


def test_a_vietnamese_ally_gives_the_imperial_skirmisher_upgrade():
    server, g = game("BRITONS", "VIETNAMESE")
    research(g, RANGE, "ELITE_SKIRMISHER_UPGRADE")
    assert ":Imperial Skirmisher:" in range_menu(server, g)


def test_no_upgrade_without_the_ally():
    for other, other_team in (("VIETNAMESE", 2), ("FRANKS", 1), ("VIETNAMESE", None)):   # an enemy, an ally of another civ
        server, g = game("BRITONS", other, other_team=other_team)
        research(g, RANGE, "ELITE_SKIRMISHER_UPGRADE")
        assert "Imperial Skirmisher" not in range_menu(server, g)
    server, g = game("BRITONS", "VIETNAMESE", team=None, other_team=None)   # no teams: all players are enemies
    research(g, RANGE, "ELITE_SKIRMISHER_UPGRADE")
    assert "Imperial Skirmisher" not in range_menu(server, g)


def test_the_turks_do_not_get_it_from_a_vietnamese_ally():
    server, g = game("TURKS", "VIETNAMESE")
    assert civs.missing(g, "IMPERIAL_SKIRMISHER_UPGRADE")


def test_a_berber_ally_gives_the_genitour_and_its_upgrade():
    server, g = game("BRITONS", "BERBERS")
    assert ":Genitour:" in range_menu(server, g) and ":Elite Genitour:" in range_menu(server, g)
    server, g = game("BRITONS", "BERBERS", other_team=2)
    assert "Genitour" not in range_menu(server, g)


def test_each_shared_unit_follows_the_rule():
    for name, owner in civs.SHARED.items():
        assert owner not in civs.MISSING.get(name, ()), name
        for civ in ("AZTECS", "BRITONS", "FRANKS"):
            ally, enemy = game(civ, owner)[1], game(civ, owner, other_team=2)[1]
            assert not civs.missing(ally, name), (name, civ)
            assert civs.missing(enemy, name) == (name in civs.MISSING), (name, civ)


def test_the_own_civilization_and_other_items_stay_as_before():
    _, g = game("VIETNAMESE", "BRITONS", other_team=2)
    assert not civs.missing(g, "IMPERIAL_SKIRMISHER_UPGRADE")
    _, g = game("BRITONS", "GURJARAS")                                 # not a team bonus unit
    assert train.civs.missing(g, "CHAKRAM_THROWER")             # train.py adds the rule to the bare civs (#1760)
