"""game/per.py: the count facts of the units and buildings (#5043). The map of test_bot_gather: player 1 (a person)
and the bot, player 2 with five villagers; they are enemies (no team)."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  (the modules that per uses)

FACTS = [(f, ">=", 0) for f in per.COUNTS] + [("unit-available", "villager"), ("building-available", "house")] + \
    [(f, "any-enemy", ">=", 0) for f in ("players-unit-count", "players-building-count", "players-civilian-population",
                                       "cc-players-unit-count", "cc-players-building-count")] + \
    [("cc-players-unit-type-count", "any-enemy", "villager", ">=", 0),
     ("cc-players-building-type-count", "any-enemy", "house", ">=", 0)]


def script(text=""):
    server, me, b = bot_map()
    me.bots = [b]                                                      # run.py: player 1 holds the bots
    for u in sorted(b.g.villagers)[3:]:
        del b.g.villagers[u]
    b.g.soldiers.update({"s0": "MILITIA", "s1": "MILITIA"})
    return per.Script(per.parse(text), b), b, me


def test_counts():
    s, b, me = script()
    assert s.check(("unit-count", "==", 5)) and s.check(("soldier-count", "==", 2))
    assert s.check(("building-count", ">=", 1)) and s.check(("players-unit-count", "any-enemy", ">", 0))
    assert s.check(("defend-soldier-count", "==", 2)) and s.check(("attack-soldier-count", "==", 0))


def test_up_get_fact_stores_the_count():
    s, b, me = script("(defrule (true) => (up-get-fact unit-count 0 7) (disable-self))")
    s.step()
    assert s.goals[7] == 5


def test_no_count_fact_is_unknown(capsys):
    s, b, me = script()
    for f in FACTS:
        s.check(f)
    assert "unknown" not in capsys.readouterr().err
