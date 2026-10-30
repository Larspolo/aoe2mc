"""game/per.py: the units, stances and age times of the other players, research-available and the taunts (#4684).
The map of test_bot_gather: player 1 (a person) and the bot, player 2; they are enemies (no team)."""
from test_per_players import script

from game.bot import build


def test_unit_count_and_stance_of_the_other_players():
    s, b, me = script()
    me.soldiers.update({f"s{i}": "MILITIA" for i in range(2)})
    assert not s.check(("players-unit-type-count", "any-enemy", "militia", ">", 2))
    me.soldiers["s2"] = "MILITIA"
    assert s.check(("players-unit-type-count", "any-enemy", "militia", ">", 2))
    assert s.check(("players-stance", 1, "enemy")) and not s.check(("players-stance", 1, "ally"))


def test_age_times():
    s, b, me = script()
    b.time = 50.0
    assert not s.check(("players-current-age-time", "any-enemy", ">", 60))
    b.time = 61.0
    assert s.check(("players-current-age-time", "any-enemy", ">", 60))
    me.techs.add(build.AGE_TECHS[0])                                  # the age up resets the time
    assert not s.check(("players-current-age-time", "any-enemy", ">", 60))
    b.time = 122.0
    assert s.check(("players-current-age-time", "any-enemy", ">", 60))
    assert s.check(("current-age-time", ">", 100))


def test_research_available_needs_no_cost():
    s, b, me = script("(defrule (taunt-detected 1 5) => (set-goal 1 1))\n"
                      "(defrule (true) => (acknowledge-taunt 1 5) (chat-local-to-self \"hi\"))")
    b.g.stock.update(food=0, gold=0)
    assert s.check(("research-available", "ri-loom")) and not s.check(("can-research", "ri-loom"))
    s.step()
    assert 1 not in s.goals and not s.warned
