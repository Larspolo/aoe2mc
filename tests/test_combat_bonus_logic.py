"""game/combat.py: a bonus adds its damage against each target of its class (#5264). The tests check the rule of
`damage` with test data and over all units of combat.STATS, not the values of game/data/units.jsonl (owner, #4177)."""
from game import combat

ATTACKER = combat.Stats(hp=100, attack=10, melee=0, pierce=0, range=0, reload=2.0, bonus={"testclass": 5}, classes=("infantry",))
TARGET = combat.Stats(hp=100, attack=1, melee=2, pierce=3, range=0, reload=2.0, classes=("testclass",))


def test_a_bonus_adds_its_damage_only_against_its_class():
    base = combat.damage("ATTACKER", "TARGET", a=ATTACKER, t=TARGET._replace(classes=()))
    assert combat.damage("ATTACKER", "TARGET", a=ATTACKER, t=TARGET) == base + 5
    assert combat.damage("ATTACKER", "TARGET", a=ATTACKER, t=TARGET._replace(classes=("otherclass",))) == base


def test_each_bonus_of_the_data_hits_each_unit_of_its_class():
    held = {c for s in combat.STATS.values() for c in s.classes}
    pairs = 0
    for name, s in combat.STATS.items():
        if name in combat.vs_units.UNITS:   # its anti-unit mode replaces its bonus against units (#4505)
            continue
        a = s._replace(attack=1000)         # a high attack: the minimum damage of 1 does not hide the bonus
        for c in sorted(c for c, v in s.bonus.items() if v > 0 and c in held):
            for target, t in combat.STATS.items():
                if c in t.classes:
                    without = t._replace(classes=tuple(x for x in t.classes if x != c))
                    assert combat.damage(name, target, a=a, t=t) > combat.damage(name, target, a=a, t=without), (name, c, target)
                    pairs += 1
    assert pairs
