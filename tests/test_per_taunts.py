"""game/per.py: taunt-detected, players-taunt-detected and acknowledge-taunt (#4827), on the map of test_bot_gather
(the bot is player 2, the person is player 1)."""
import diplomacy  # noqa: E402
from test_bot_gather import bot_map

from game import per
from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)

RULES = """(defrule (taunt-detected 1 31) => (set-goal 1 1))
(defrule (taunt-detected 1 32) => (set-goal 2 1))
(defrule (players-taunt-detected any-ally 31) => (set-goal 3 1))
(defrule (goal 4 1) => (acknowledge-taunt 1 31))"""


def run(ally):
    server, me, b = bot_map()
    if ally:
        for p in ("1", "2"):
            b.g.players.setdefault(p, {})["team"] = 1
    assert (diplomacy.stance(b.g, 1) == "ally") == ally
    s = per.Script(per.parse(RULES), b)
    s.step()
    assert not s.goals                                     # no taunt yet
    me.taunted = [*getattr(me, "taunted", []), "31"]       # as gather.Game.clicks keeps them
    s.step()
    return s


def test_a_taunt_of_an_ally_is_detected_until_acknowledged():
    s = run(True)
    assert s.goals == {1: 1, 3: 1}
    s.goals.clear()
    s.goals[4] = 1
    s.step()                                               # the acknowledge runs after the facts of this pass
    s.goals = {4: 0}
    s.step()
    assert s.goals == {4: 0}


def test_the_taunt_of_an_enemy_is_not_an_ally_taunt():
    s = run(False)
    assert s.goals == {1: 1}
