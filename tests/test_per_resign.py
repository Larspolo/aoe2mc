"""game/per.py: the action resign puts the bot out, as the cheat (#4826, item 9), on the map of test_bot_gather
(the bot is player 2, the person is player 1). The taunts 104 and 105 are read by the script itself."""
from test_bot_gather import bot_map

from game import conquest, per
from game.bot import build  # noqa: F401  (puts game/ on the path for the plain names)

RULES = """(defrule (taunt-detected 1 104) => (set-goal 1 1))
(defrule (goal 1 -1) => (resign))"""   # goal 1 is -1 (not set) until the taunt sets it


def run(taunted):
    server, me, b = bot_map()
    for o in b.g.data["objects"]:                              # the trees and mines of the map have no owner: gaia
        o.setdefault("player", 0)
    s = per.Script(per.parse(RULES), b)
    if taunted:
        me.taunted = ["104"]                                   # as gather.Game.clicks keeps them
    s.step()
    return vars(conquest.main(b.g)).get("defeated", set())   # the person's Gather keeps the set


def test_the_bot_resigns_with_no_taunt():
    assert 2 in run(False)


def test_a_taunt_of_dont_resign_keeps_the_bot_in():
    assert 2 not in run(True)


def test_resign_gives_no_action_warning(capsys):
    run(False)
    assert "action" not in capsys.readouterr().err
