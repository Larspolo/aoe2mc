"""game/civs.py: the military units of a player get the hit point, attack, armor, range, reload and walk speed bonuses
of the own civilization (AoE2 DE, #1090)."""
import pytest

import buildings

from game import ai, civs, combat, gather, train

from test_civ_work import setup


def trained(civ, name, techs=()):
    """The commands of a unit `name` that player 1 of civilization civ trains, with the technologies techs."""
    g = setup(civ)
    g.techs.update(techs)
    n = len(g.game.log)
    uuid = train.summon(g, name, (8.5, 64.0, 8.5), player=1)
    return g, uuid, g.game.log[n:]


def test_a_frankish_knight_has_20_percent_more_hit_points_from_the_feudal_age():
    _, uuid, log = trained("FRANKS", "KNIGHT", {"FEUDAL_AGE"})
    assert f"aoe stats {uuid} 120 " in " ".join(log)
    _, uuid, log = trained("GOTHS", "KNIGHT", {"FEUDAL_AGE"})
    assert f"aoe stats {uuid} 100 " in " ".join(log)
    assert train.stats(setup("FRANKS"), "KNIGHT").hp == 100              # the Dark Age: no bonus yet


def test_the_bonus_comes_before_the_technologies():
    g = setup("FRANKS")
    g.techs.update({"FEUDAL_AGE", "BLOODLINES"})
    assert train.stats(g, "SCOUT_CAVALRY").hp == 45 * 1.2 + 20


def test_celtic_infantry_walks_faster_in_each_age():
    T = setup("CELTS").map.T
    for techs, factor in (((), 1.05), (("FEUDAL_AGE",), 1.1), (("FEUDAL_AGE", "CASTLE_AGE"), 1.15)):
        _, uuid, log = trained("CELTS", "MILITIA", techs)
        speed = ai.movement_speed("MILITIA", T, gather.NORMAL * factor)
        assert f"attribute {uuid} minecraft:movement_speed base set {speed}" in log
    _, uuid, log = trained("GOTHS", "MILITIA")
    assert f"attribute {uuid} minecraft:movement_speed base set {ai.movement_speed('MILITIA', T)}" in log


def test_more_bonuses():
    def stats(civ, name, *techs):
        g = setup(civ)
        g.techs.update(techs)
        return train.stats(g, name)
    archer = combat.stats("ARCHER")
    assert stats("BRITONS", "ARCHER", "FEUDAL_AGE", "CASTLE_AGE").range == archer.range + 1
    assert stats("BRITONS", "SKIRMISHER", "FEUDAL_AGE", "CASTLE_AGE") == combat.stats("SKIRMISHER")
    assert stats("TEUTONS", "KNIGHT", "FEUDAL_AGE", "CASTLE_AGE").melee == combat.stats("KNIGHT").melee + 1
    assert stats("SARACENS", "CAMEL_RIDER").hp == 125
    assert stats("VIETNAMESE", "SKIRMISHER").hp == 36
    assert stats("TURKS", "SCOUT_CAVALRY").pierce == combat.stats("SCOUT_CAVALRY").pierce + 1
    assert stats("MONGOLS", "CAVALRY_ARCHER").reload == pytest.approx(combat.stats("CAVALRY_ARCHER").reload / 1.25,
                                                                      abs=1e-3)
    assert stats("MALIANS", "SPEARMAN", "FEUDAL_AGE").pierce == combat.stats("SPEARMAN").pierce + 1
    assert stats("MALIANS", "GBETO", "FEUDAL_AGE") == combat.stats("GBETO")          # a castle unit
    assert civs.speed(setup("BERBERS"), "VILLAGER") == 1.05


def test_the_table_names_known_civilizations_and_groups_in_order():
    assert list(civs.UNITS) == sorted(civs.UNITS)                     # a civilization without a castle unit too (Shu)
    assert set(civs.UNITS) <= {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    assert list(civs.GROUPS) == sorted(civs.GROUPS)
    for civ, rules in civs.UNITS.items():
        for group, value, change in rules:
            assert len(change) == 4 and (value in ("speed", "taken") or value in combat.Stats._fields), civ
            assert any(civs.GROUPS[group](n, s) for n, s in combat.STATS.items()), group


def test_the_live_celtic_infantry_walks_faster_after_an_age():
    g, uuid, _ = trained("CELTS", "MILITIA")
    n = len(g.game.log)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    speed = ai.movement_speed("MILITIA", g.map.T, gather.NORMAL * 1.1)
    assert f"attribute {uuid} minecraft:movement_speed base set {speed}" in g.game.log[n:]
