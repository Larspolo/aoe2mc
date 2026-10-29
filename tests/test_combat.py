"""game/combat.py: the AoE2 combat values of the game program (#513)."""
import scenarios

import aoe2mc
from game import combat


def test_the_fallback_values():
    assert combat.stats("PALISADE_WALL") == combat.BUILDING
    assert combat.stats("NO_SUCH_UNIT") == combat.DEFAULT


def test_each_object_of_the_battle_scenario_has_values(tmp_path):
    *_, objects, _ = aoe2mc.read_scenario(scenarios.battle(str(tmp_path / "battle.aoe2scenario")))
    names = {(o["kind"], o["name"]) for o in objects if o["player"]}
    assert {n for k, n in names if k == "U"} - set(combat.STATS) == set()
    assert {n for k, n in names if k == "B"} - set(combat.BUILDINGS) - {"GUARD_TOWER"} == set()
    assert all(s.hp > 0 and s.range >= 0 and s.reload >= 0 for s in [*combat.STATS.values(), *combat.BUILDINGS.values()])
