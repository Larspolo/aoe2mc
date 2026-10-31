"""The target priorities of an AI script (#4968): up-set-offense-priority, up-set-defense-priority,
up-reset-target-priorities and up-update-targets on the attack wave and the town defense of the bot."""
from test_bot_attack import armed, orders
from test_bot_defend import town
from test_per_up_search import run

from game import combat, owners, per


def scripted(b):
    b.script = per.Script([], b)
    b.script.sn["sn-minimum-attack-group-size"] = 2                    # the two militia are one wave
    return b.script


def test_offense_priority_puts_a_building_before_a_villager():
    server, me, b = armed(attack=0.0)
    s = scripted(b)
    tc = combat.target_uuid([2, 2, 5, 5])                              # the town center of player 1
    server.forts.add(tc)
    server.entities["p1"]["Pos"] = (12.5, 64.0, 24.5)                  # the villager is nearer than the town center
    run(s, "(set-strategic-number sn-enable-offensive-priority 1) (up-set-offense-priority c: town-center c: 11)")
    b.fight()
    assert sorted(orders(server)) == [["m0", tc], ["m1", tc]]
    run(s, "(up-reset-target-priorities priority-offense 0)")          # the old order: the villager
    b.targets, n = {}, len(server.log)
    b.fight()
    assert sorted(orders(server, n)) == [["m0", "p1"], ["m1", "p1"]] and not s.warned


def test_offense_priority_needs_the_strategic_number():
    server, me, b = armed(attack=0.0)
    s = scripted(b)
    server.forts.add(combat.target_uuid([2, 2, 5, 5]))
    run(s, "(up-set-offense-priority c: town-center c: 11)")           # sn-enable-offensive-priority is 0
    b.fight()
    assert sorted(orders(server)) == [["m0", "p1"], ["m1", "p1"]]


def test_defense_priority_and_update_targets_with_two_enemies_in_the_town():
    server, me, b = town()
    s = scripted(b)
    me.soldiers["e2"] = "KNIGHT"
    owners.add(me, "e2", "KNIGHT", 1)
    server.entities["e2"] = {"Pos": (17.5, 64.0, 21.5), "Rotation": (0.0, 0.0)}   # farther than e1
    b.step()
    assert sorted(orders(server)) == [["m0", "e1"], ["m1", "e1"]]
    run(s, "(up-set-defense-priority c: knight c: 1000)")
    n = len(server.log)
    b.step()
    assert orders(server, n) == []                                     # the guards keep their targets until an update
    run(s, "(up-update-targets)")
    b.step()
    assert sorted(orders(server, n)) == [["m0", "e2"], ["m1", "e2"]]
    run(s, "(up-reset-target-priorities priority-bogus 0)")
    assert s.warned == {("priority type", "priority-bogus")}
