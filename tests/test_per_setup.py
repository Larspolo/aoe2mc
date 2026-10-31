"""game/per.py: the facts of the game setup and the symbols of #load-if-defined (#4683). The map of test_bot_gather:
player 1 (a person) and the bot, player 2."""
from test_bot_gather import bot_map

from game import per


def script(civs=("FRANKS", "BRITONS")):
    server, me, b = bot_map()
    me.bots = [b]
    for p, c in zip((1, 2), civs):
        b.g.data["players"].setdefault(str(p), {})["civ"] = c
    return per.Script(per.parse(""), b), b


def test_the_civilization_facts():
    s, b = script()
    assert s.check(("civ-selected", "britons")) and not s.check(("civ-selected", "franks"))
    assert s.check(("players-civ", "any-enemy", "franks")) and not s.check(("players-civ", "any-enemy", "britons"))


def test_the_setup_facts():
    s, b = script()
    b.difficulty = "hard"
    assert s.check(("difficulty", "==", "hard")) and s.check(("difficulty", "<", "moderate"))
    assert not s.check(("death-match-game",)) and not s.check(("regicide-game",))
    b.g.modes = frozenset({"death-match", "regicide"})
    assert s.check(("death-match-game",)) and s.check(("regicide-game",))
    assert s.check(("starting-age", "==", "dark-age"))
    b.g.start_age = "castle"
    assert s.check(("starting-age", "==", "castle-age")) and s.check(("starting-age", ">", "feudal-age"))
    assert s.check(("map-type", "scenario-map"))
    size = per.map_size(b.g.data)
    assert s.check(("map-size", size)) and not s.check(("map-size", "ludikris-map" if size != "ludikris-map" else "tiny-map"))


def test_load_if_defined_takes_the_symbols_of_the_bot():
    s, b = script()
    defined = per.symbols(b.g.data, 2, "hard", {"death-match"}, "castle")
    assert {"britons-civ", "difficulty-hard", "death-match", "castle-age-start", "scenario-map"} <= defined
    text = """#load-if-defined BRITONS-CIV
(defrule (true) => (set-goal 1 1))
#else
(defrule (true) => (set-goal 1 2))
#end-if
#load-if-defined DIFFICULTY-HARD
(defrule (true) => (set-goal 2 1))
#end-if"""
    s = per.Script(per.parse(text, defined), b)
    s.step()
    assert s.goals == {1: 1, 2: 1}
