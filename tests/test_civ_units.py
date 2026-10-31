"""game/civs.py: the military units of a player get the hit point, attack, armor, range, reload and walk speed bonuses
of the own civilization (AoE2 DE, #1090)."""
import pytest
from test_civ_work import setup

import buildings
from game import ai, civs, combat, train


def trained(civ, name, techs=()):
    """The commands of a unit `name` that player 1 of civilization civ trains, with the technologies techs."""
    g = setup(civ)
    g.techs.update(techs)
    n = len(g.game.log)
    uuid = train.summon(g, name, (8.5, 64.0, 8.5), player=1)
    return g, uuid, g.game.log[n:]


def stats(civ, name, *techs):
    g = setup(civ)
    g.techs.update(techs)
    return train.stats(g, name)


def speed(log, uuid):
    """The movement speed that the log sets for uuid."""
    return next(float(c.split()[-1]) for c in log if c.startswith(f"attribute {uuid} minecraft:movement_speed base set "))


def test_a_frankish_knight_has_more_hit_points_from_the_feudal_age():
    g, uuid, log = trained("FRANKS", "KNIGHT", {"FEUDAL_AGE"})
    hp = train.stats(g, "KNIGHT").hp
    assert hp > combat.stats("KNIGHT").hp and f"aoe stats {uuid} {hp} " in " ".join(log)
    _, uuid, log = trained("GOTHS", "KNIGHT", {"FEUDAL_AGE"})
    assert f"aoe stats {uuid} {combat.stats('KNIGHT').hp} " in " ".join(log)
    assert train.stats(setup("FRANKS"), "KNIGHT").hp == combat.stats("KNIGHT").hp   # the Dark Age: no bonus yet


def test_the_bonus_comes_before_the_technologies():
    bloodlines = stats("GOTHS", "SCOUT_CAVALRY", "FEUDAL_AGE", "BLOODLINES").hp - stats("GOTHS", "SCOUT_CAVALRY", "FEUDAL_AGE").hp
    assert stats("FRANKS", "SCOUT_CAVALRY", "FEUDAL_AGE", "BLOODLINES").hp == pytest.approx(
        stats("FRANKS", "SCOUT_CAVALRY", "FEUDAL_AGE").hp + bloodlines)


def test_celtic_infantry_walks_faster_in_each_age():
    T = setup("CELTS").map.T
    seen = []
    for techs in ((), ("FEUDAL_AGE",), ("FEUDAL_AGE", "CASTLE_AGE")):
        _, uuid, log = trained("CELTS", "MILITIA", techs)
        seen.append(speed(log, uuid))
    _, uuid, log = trained("GOTHS", "MILITIA")
    assert f"attribute {uuid} minecraft:movement_speed base set {ai.movement_speed('MILITIA', T)}" in log
    assert ai.movement_speed("MILITIA", T) < seen[0] < seen[1] < seen[2], seen


def test_the_table_names_known_civilizations_and_groups_in_order():
    assert list(civs.UNITS) == sorted(civs.UNITS)                     # a civilization without a castle unit too (Shu)
    assert set(civs.UNITS) <= {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    assert list(civs.GROUPS) == sorted(civs.GROUPS)
    for civ, rules in civs.UNITS.items():
        for group, value, change in rules:
            assert len(change) == 4 and (value in ("friendly", "speed", "taken") or value in combat.Stats._fields or value.startswith("bonus:")), civ
            assert any(civs.GROUPS[group](n, s) for n, s in combat.STATS.items()), group


def test_the_live_celtic_infantry_walks_faster_after_an_age():
    g, uuid, _ = trained("CELTS", "MILITIA")
    n = len(g.game.log)
    train.research(g, {"name": "FEUDAL_AGE", "player": "Steve"})
    _, new, log = trained("CELTS", "MILITIA", ("FEUDAL_AGE",))         # a new unit of the Feudal Age
    assert speed(g.game.log[n:], uuid) == speed(log, new)
