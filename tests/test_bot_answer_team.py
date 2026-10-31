"""The lines of an allied bot to a taunt go to the team of the ally who asked: no person is in the team of the bot
(#5051, found by the check #5022)."""
from test_bot_ally_answers import ALLY, make

from game import build


def test_the_answer_to_taunt_42_goes_to_the_team_of_the_asker():
    b, sent = make(ALLY, ["42"], techs=(build.AGE_TECHS[0],))
    b.answer()
    assert len(sent) == 1 and sent[0].startswith("tellraw @a[team=p1] ")
