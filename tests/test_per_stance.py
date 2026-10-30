"""game/per.py: set-stance and stance-toward (#4574), on the map of test_bot_gather (the bot is player 2)."""
import diplomacy  # noqa: E402
from test_bot_gather import bot_map

from game import per
from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)

RULES = "(defrule (game-time > 60) => (set-stance 1 ally)) (defrule (stance-toward 1 ally) => (set-goal 1 1))"


def run(unlock, time):
    server, me, b = bot_map()
    b.g.data["unlock_teams"] = unlock
    s = per.Script(per.parse(RULES), b)
    b.time = time
    s.step()
    return s, b


def test_set_stance_makes_an_ally_and_stance_toward_reads_it():
    s, b = run(True, 30)
    assert diplomacy.stance(b.g, 1) != "ally" and 1 not in s.goals
    b.time = 61
    s.step()
    assert diplomacy.stance(b.g, 1) == "ally" and s.goals[1] == 1


def test_locked_teams_do_not_change(capsys):
    s, b = run(False, 61)
    before = diplomacy.stance(b.g, 1)
    s.step()
    assert diplomacy.stance(b.g, 1) == before != "ally" and 1 not in s.goals
    assert capsys.readouterr().err == ""
