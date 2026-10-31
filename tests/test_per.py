"""game/per.py: parse() reads an AoE2 AI script (.per) into rules (#4527). Own small scripts, no file of the game."""
import pytest

from game import per

SCRIPT = """
; a comment (defrule (false) => (do-nothing))
(defconst MAX-VILLAGERS 30)
(defconst gl-step 101)
(DefRule
    (Food-Amount >= 50)         ; the case does not matter
    (civilian-population less-than max-villagers)
    (can-train villager)
=>
    (train villager)
    (chat-to-all "Train a Villager; now")
    (set-goal gl-step -1))
(defrule
    (or (and (current-age == feudal-age) (not (goal gl-step 0)))
        (nor (true) (false)))
    (nand (game-time > 600) (timer-triggered 1))
=>
    (disable-self))
"""


def test_rules_facts_and_actions():
    """Each defrule gives its facts and actions in the order of the file, with the constants replaced."""
    first, second = per.parse(SCRIPT)
    assert first.facts == (("food-amount", ">=", 50), ("civilian-population", "<", 30), ("can-train", "villager"))
    assert first.actions == (("train", "villager"), ("chat-to-all", "Train a Villager; now"), ("set-goal", 101, -1))
    assert isinstance(first.actions[1][1], per.Text) and first.line == 5
    assert second.facts == (
        ("or", ("and", ("current-age", "==", "feudal-age"), ("not", ("goal", 101, 0))), ("nor", ("true",), ("false",))),
        ("nand", ("game-time", ">", 600), ("timer-triggered", 1)))
    assert second.actions == (("disable-self",),)


@pytest.mark.parametrize("word, op", sorted(per.REL.items()))
def test_relational_words(word, op):
    """The words and the symbols of the relational operators give the symbol."""
    (rule,) = per.parse(f"(defrule (wood-amount {word} 100) => (build house))")
    assert rule.facts == (("wood-amount", op, 100),)


COND = """
#load-if-defined DEATH-MATCH
(defrule (true) => (chat-to-all "dm"))
  #load-if-not-defined LAND-MAP
  (defrule (true) => (chat-to-all "dm water"))
  #else
  (defrule (true) => (chat-to-all "dm land"))
  #end-if
#else
(defrule (true) => (chat-to-all "random"))
#end-if
(defrule (true) => (chat-to-all "all"))
"""


@pytest.mark.parametrize("defined, texts", [
    ((), ["random", "all"]),
    (("death-match",), ["dm", "dm water", "all"]),
    (("Death-Match", "land-map"), ["dm", "dm land", "all"]),
    (("land-map",), ["random", "all"]),
])
def test_load_if_defined(defined, texts):
    """#load-if-defined keeps the text by the defined symbols, also nested, with #else."""
    assert [r.actions[0][1] for r in per.parse(COND, defined)] == texts


def test_load(tmp_path):
    """(load "...") reads a file of the AI folder (".per" added, backslashes as folders, any case) with the same
    constants."""
    (tmp_path / "My").mkdir()
    (tmp_path / "My" / "Eco.per").write_text("(defrule (food-amount > LIMIT) => (train villager))\n")
    (tmp_path / "main.per").write_text('(defconst limit 50)\n(load "my\\\\eco")\n(defrule (true) => (do-nothing))\n')
    eco, last = per.read(tmp_path / "main.per")
    assert eco.facts == (("food-amount", ">", 50),) and eco.file.endswith("Eco.per") and eco.line == 1
    assert last.actions == (("do-nothing",),) and last.line == 3


@pytest.mark.parametrize("text, line", [
    ("(defrule (true) => (train villager)", 1),                # no )
    ("\n(defrule (true) (train villager))", 2),                # no =>
    ("(defrule => (train villager))", 1),                      # no fact
    ("\n\n(defrule (true) =>)", 3),                            # no action
    ("(defrule (true) => (train villager)))", 1),              # a ) too many
    ("(defrule true => (train villager))", 1),                 # a fact without ( )
    ("(defrule (not (true) (false)) => (do-nothing))", 1),     # not takes one fact
    ("(defrule (and (true)) => (do-nothing))", 1),             # and takes two or more
    ("(defconst a 1)\n(defconst A 2)", 2),                     # a constant again
    ("(defconst a b)", 1),                                     # no number
    ('\n(load "missing")', 2),                                 # no file
    ('(defrule (true) => (chat-to-all "no end))', 1),          # a text with no end quote
    ("#load-if-defined\n(defrule (true) => (do-nothing))", 1),  # no symbol
    ("\n#else", 2),                                            # no #load-if-defined
])
def test_broken_script(text, line):
    """A broken script gives a ValueError that names its line."""
    with pytest.raises(ValueError, match=rf"^<script>:{line}: "):
        per.parse(text)


def test_open_if():
    """A #load-if-defined with no #end-if gives a ValueError."""
    with pytest.raises(ValueError, match="no #end-if"):
        per.parse("#load-if-defined X\n(defrule (true) => (do-nothing))")


def test_unknown_form(capsys):
    """An unknown top-level form gives one warning line, and the other rules stay."""
    rules = per.parse("(load-nothing 50 \"a\")\n(defrule (true) => (do-nothing))")
    assert len(rules) == 1 and "unknown form load-nothing" in capsys.readouterr().err
