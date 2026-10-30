"""game/per.py: an AI script sets the gather shares and the attack of its bot with strategic numbers (#4530)."""
from test_bot_attack import armed, orders, steps
from test_bot_gather import bot_map

from game import per

SHARES = """(defrule (true) => (set-strategic-number sn-food-gatherer-percentage 20)
 (set-strategic-number sn-wood-gatherer-percentage 40) (set-strategic-number sn-gold-gatherer-percentage 20)
 (set-strategic-number sn-stone-gatherer-percentage 20) (disable-self))"""


def test_the_idle_villagers_go_by_the_gatherer_percentages():
    server, me, b = bot_map()
    b.script = per.Script(per.parse(SHARES), b)
    for _ in range(50):
        b.step()
    assert b.shares() == {"food": 0.2, "wood": 0.4, "gold": 0.2, "stone": 0.2}
    assert sorted(v.res for v in b.g.villagers.values()) == ["food", "gold", "stone", "wood", "wood"]


def test_the_strategic_number_fact_reads_the_set_value():
    server, me, b = bot_map()
    b.script = per.Script(per.parse(SHARES + "(defrule (strategic-number sn-wood-gatherer-percentage == 40) "
                                    "=> (set-goal 1 7))"), b)
    b.step()
    assert b.script.goals == {1: 7}


def test_an_unknown_strategic_number_warns_once(capsys):
    server, me, b = bot_map()
    b.script = per.Script(per.parse("(defrule (true) => (set-strategic-number sn-nothing 3))"), b)
    b.step()
    b.step()
    assert capsys.readouterr().err.count("unknown strategic number sn-nothing") == 1 and b.script.sn == {}


def attack_script(minimum, maximum=0):
    return per.parse(f"""(defrule (true) => (set-strategic-number sn-minimum-attack-group-size {minimum})
 (set-strategic-number sn-maximum-attack-group-size {maximum}) (disable-self))
(defrule (goal 1 1) => (attack-now) (disable-self))""")


def test_no_soldier_attacks_before_attack_now():
    server, me, b = armed(n=3, attack=0.0)
    b.script = per.Script(attack_script(3), b)
    steps(b, 120)
    assert orders(server) == []
    b.script.goals[1] = 1
    steps(b, 5)
    assert sorted(o[0] for o in orders(server)) == ["m0", "m1", "m2"]


def test_the_wave_waits_for_the_minimum_and_keeps_the_maximum():
    server, me, b = armed(n=3, attack=0.0)
    b.script = per.Script(attack_script(4), b)
    b.script.goals[1] = 1
    steps(b, 20)
    assert orders(server) == []                                        # 3 soldiers, a minimum of 4
    server, me, b = armed(n=3, attack=0.0)
    b.script = per.Script(attack_script(2, 2), b)
    b.script.goals[1] = 1
    steps(b, 5)
    assert sorted({o[0] for o in orders(server)}) == ["m0", "m1"]
