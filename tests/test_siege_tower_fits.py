"""A siege tower takes only infantry, foot archers and villagers (AoE2 wiki "Siege Tower"): no mounted archer (#3118)."""
import types

from game import combat, siege_tower


def game(units):
    return types.SimpleNamespace(villagers={}, soldiers=dict(units))


def test_camel_archers_do_not_fit_a_siege_tower():
    for name in ("CAMEL_ARCHER", "ELITE_CAMEL_ARCHER"):
        assert not siege_tower.fits(game({"u": name}), "u")


def test_foot_archers_infantry_and_villagers_fit_a_siege_tower():
    g = game({"a": "ARCHER", "m": "MILITIA", "v": "VILLAGER"})
    g.villagers["v"] = object()
    assert siege_tower.fits(g, "a") and siege_tower.fits(g, "m") and siege_tower.fits(g, "v")


def test_no_mounted_unit_fits_a_siege_tower():
    for name, s in combat.STATS.items():
        if set(s.classes) & {combat.CAV, combat.CAM, combat.ELE}:
            assert not siege_tower.fits(game({"u": name}), "u"), name
