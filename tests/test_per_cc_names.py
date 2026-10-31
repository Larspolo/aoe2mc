"""The airef names of fe-cc-effect-amount (#5130): an effect and an attribute by their names of per_names.jsonl give the
same stat as their numbers; a name the game program does not change gives the one warning "cheat effect"."""
from test_per_up_search import run, script

from game import train


def militia_hp(cheat):
    s, b, _ = script()
    b.g.cheats = True
    hp = train.stats(b.g, "MILITIA").hp
    run(s, cheat)
    return train.stats(b.g, "MILITIA").hp - hp, s


def test_the_names_give_the_stat_of_the_numbers():
    named, s = militia_hp("(fe-cc-effect-amount effect-add-attribute militiaman attribute-hp 10)")
    number, _ = militia_hp("(fe-cc-effect-amount 4 militiaman 0 10)")
    assert named == number == 10 and not s.warned


def test_an_unchanged_effect_or_attribute_gives_one_warning():
    for cheat in ("(fe-cc-effect-amount effect-mod-resource militiaman attribute-hp 10)",
                  "(fe-cc-effect-amount effect-add-attribute militiaman attribute-los 10)"):
        change, s = militia_hp(cheat)
        assert change == 0 and len(s.warned) == 1
