"""The airef forms of up-compare-text (index of a text constant) and players-civ my-civ (#5232)."""
import civs
from test_per_rules import run


def test_up_compare_text_with_a_text_constant_gives_the_index():
    s, b, _ = run("""(defconst text-name-one "one") (defconst text-name-two "two")
(defrule (true) => (up-store-text "player one") (disable-self))
(defrule (up-compare-text c: text-name-one >= 0) => (set-goal 1 1))
(defrule (up-compare-text c: text-name-two >= 0) => (set-goal 2 1))""")
    assert s.goals == {1: 1}
    assert not s.warned


def test_players_civ_my_civ_compares_with_the_civ_of_the_bot():
    s, b, _ = run("(defrule (players-civ any-enemy my-civ) => (set-goal 1 1))")
    mine = civs.real(b.g, b.g.player)
    enemies = [p for p in b.g.players if str(p) != str(b.g.player)]
    want = any(civs.real(b.g, p) == mine for p in enemies)
    assert s.goals == ({1: 1} if want else {})
    assert not s.warned
