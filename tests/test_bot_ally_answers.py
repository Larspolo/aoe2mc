"""A bot answers the taunts 42 to 44 of an allied person with one line to its team, as the AoE2 AI does (#4829)."""
import json
import types

from game import bot, build


def make(players, taunted, techs=()):
    """A bot with a fake game: one person who sent the taunts, and the lines that the bot sends."""
    sent = []
    person = types.SimpleNamespace(player=1, taunted=list(taunted))
    g = types.SimpleNamespace(player=2, players=players, peers=[person], techs=techs, command=sent.append,
                              stock={"food": 120, "wood": 80, "gold": 30, "stone": 5})
    b = bot.Bot.__new__(bot.Bot)
    b.g, b.attack, b.said = g, 600.0, {}
    return b, sent


def text_of(line):
    return json.loads(line.split(" ", 2)[2])["text"]


ALLY = {"1": {"team": 1}, "2": {"team": 1}}
ENEMY = {"1": {}, "2": {"team": 1}}


def test_an_ally_taunt_42_gives_one_line_with_the_age_of_the_bot():
    b, sent = make(ALLY, ["42"], techs=(build.AGE_TECHS[0],))
    b.answer()
    assert len(sent) == 1 and sent[0].startswith("tellraw @a[team=p1] ")
    assert text_of(sent[0]) == bot.ANSWERS["42"].format(age=build.AGE_NAMES[1])


def test_an_ally_taunt_44_gives_one_line_with_the_stock_of_the_bot():
    b, sent = make(ALLY, ["44"])
    b.answer()
    assert len(sent) == 1
    assert text_of(sent[0]) == bot.ANSWERS["44"].format(food=120, wood=80, gold=30, stone=5)


def test_an_enemy_taunt_gives_no_line():
    b, sent = make(ENEMY, ["42", "44"])
    b.answer()
    assert sent == []


def test_a_taunt_is_answered_once():
    b, sent = make(ALLY, ["42"])
    b.answer()
    b.answer()
    assert len(sent) == 1
