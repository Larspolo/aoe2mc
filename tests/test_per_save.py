"""A saved game keeps the AI script state of each bot: goals, timers, disabled rules, strategic numbers (#4575)."""
from test_savegame_bots import game

from game import per, savegame

SCRIPT = """(defrule (true) => (set-goal 1 5) (enable-timer 2 30) (set-strategic-number sn-wood-gatherer-percentage 40)
 (disable-self))
(defrule (goal 1 5) => (set-goal 3 1))"""


def scripted(me):
    for b in me.bots:
        b.script = per.Script(per.parse(SCRIPT), b)
    return me


def test_a_load_keeps_the_goals_timers_numbers_and_disabled_rules():
    me = scripted(game(("standard",) * 3, (1, 1, 1)))
    s = me.bots[0].script
    s.step()
    s.goals[1] = 9                                                     # after the step: the disabled rule must not set 5
    new = scripted(game(("standard",) * 3, (1, 1, 1)))
    savegame.load(new, savegame.dump(me))
    t = new.bots[0].script
    assert (t.goals, t.timers, t.sn, t.off) == (s.goals, s.timers, s.sn, s.off) and t.goals[1] == 9
    t.step()
    assert t.goals[1] == 9
    assert new.bots[1].script.goals == {}                              # a bot whose script did not run yet


def test_a_save_with_no_script_state_loads():
    me = game(("standard",) * 3, (1, 1, 1))
    state = savegame.dump(me)
    new = scripted(game(("standard",) * 3, (1, 1, 1)))
    savegame.load(new, state)
    assert new.bots[0].script.goals == {}
