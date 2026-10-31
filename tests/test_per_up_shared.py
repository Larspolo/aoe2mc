"""Shared goals of allied AI scripts and the signals and events of a script (up-get-shared-goal, up-set-shared-goal,
up-get-signal, up-set-signal, up-get-event, up-set-event; airef, #4878)."""
import types

import per
from test_per_bot import scripted


def ally(b, player):
    """The script of a second bot of the game of b: its Gather shares the main Gather of b (conquest.main)."""
    g = types.SimpleNamespace(player=player, players=b.g.players, peers=[], share=b.g.share or b.g)
    return per.Script([], types.SimpleNamespace(g=g))


def teams(b, **team):
    for p, t in team.items():
        b.g.players.setdefault(p[1:], {})["team"] = t


def test_a_shared_goal_that_one_script_sets_is_the_value_of_its_ally():
    b = scripted("(defrule (true) => (set-goal 4 7) (up-set-shared-goal c: 3 g: 4) (disable-self))")
    teams(b, p2=1, p3=1, p4=2)
    friend, foe = ally(b, 3), ally(b, 4)
    b.script.step()
    for s in (friend, foe):
        s.act(0, ("up-get-shared-goal", "c:", 3, 5))
    assert friend.goals[5] == 7 and foe.goals[5] == 0                  # an enemy team has its own table


def test_up_set_signal_and_up_set_event_are_the_values_of_up_get_signal_and_up_get_event():
    b = scripted("""(defrule (true) => (set-goal 1 2) (up-set-signal c: 1 c: 9) (up-set-event g: 1 c: 6)
(up-get-signal c: 1 10) (up-get-event c: 2 11) (up-get-signal c: 5 12) (disable-self))""")
    b.script.step()
    goals = b.script.goals
    assert goals[10] == 9 and goals[11] == 6 and goals[12] == 0       # g: 1 holds the event id 2
