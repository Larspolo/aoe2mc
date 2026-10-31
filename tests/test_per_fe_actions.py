"""The DE fe- actions of an AI script (#5048): fe-exclude-from-attack-group and its reset, fe-filter-garrisoned,
fe-cc-effect-amount and -percent (cheats only), fe-set-signal and fe-break-point. The maps of test_bot_attack and
test_per_up_filters."""
from test_bot_attack import armed, orders, steps
from test_per_up_filters import found
from test_per_up_search import run, script

from game import per, train


def oid(s, key):
    return next(i for i, k, _, _ in s.objects(s.bot.g) if k == key)


def test_an_excluded_soldier_stays_home_until_the_reset():
    server, me, b = armed(n=2, attack=0.0)
    b.group = 1                                                        # each soldier is a wave
    s = per.Script([], b)
    run(s, f"(fe-exclude-from-attack-group c: {oid(s, 'm0')})")
    steps(b, 4)
    assert [u for u, _ in orders(server)] == ["m1"]
    run(s, "(fe-reset-attack-group-exclusion-list)")
    start = len(server.log)
    steps(b, 4)
    assert [u for u, _ in orders(server, start)] == ["m0"] and not s.warned


def test_filter_garrisoned_keeps_the_garrisoned_objects():
    s, b, me = script()
    assert found(s, "(fe-filter-garrisoned c: 1) (up-find-local c: villager-class c: 20)") == (0, 0)
    b.g.garrisons[(20, 23, 20, 23)] = ["b0", "b1"]
    assert found(s, "(up-find-local c: villager-class c: 20)") == (2, 0)
    run(s, "(up-reset-filters)")
    assert found(s, "(up-find-local c: villager-class c: 20)") == (5, 0) and not s.warned


def test_cc_effect_changes_the_attribute_only_with_the_cheats():
    s, b, me = script()
    hp = train.stats(b.g, "MILITIA").hp
    run(s, "(fe-cc-effect-amount 4 militiaman 0 10)")
    assert train.stats(b.g, "MILITIA").hp == hp and len(s.warned) == 1
    b.g.cheats = True
    run(s, "(fe-cc-effect-amount 4 militiaman 0 10)")
    assert train.stats(b.g, "MILITIA").hp == hp + 10
    run(s, "(fe-cc-effect-percent 5 militiaman 0 200)")
    assert train.stats(b.g, "MILITIA").hp == 2 * (hp + 10) and len(s.warned) == 1


def test_no_fe_action_is_unknown():
    s, b, me = script()
    run(s, "(fe-break-point 0 0 0 0) (fe-set-signal c: 3 c: 7) (up-get-signal c: 3 50)")
    assert s.goals[50] == 7 and not s.warned
