"""game/per.py: (load-random ...) loads one file of a list at random, as the AoE2 interpreter does (#5099). A percent is the
chance of the next file, a file with no percent is the default, and +NAME takes the percent from a constant."""
import numpy as np
import pytest

from game import per


def write(folder, name, text):
    (folder / f"{name}.per").write_text(text, encoding="utf-8")


def rules_of(folder, text, seed=0):
    return per.parse(text, folder=str(folder), rng=np.random.default_rng(seed))


def test_a_hundred_percent_loads_the_first_file(tmp_path):
    write(tmp_path, "a", "(defrule (true) => (up-chat \"from a\"))")
    write(tmp_path, "b", "(defrule (true) => (up-chat \"from b\"))")
    rules = rules_of(tmp_path, '(load-random 100 "a" "b")')
    assert len(rules) == 1 and rules[0].actions[0][0] == "up-chat" and rules[0].actions[0][1] == "from a"


def test_zero_percent_loads_the_default_file(tmp_path):
    write(tmp_path, "a", "(defrule (true) => (up-chat \"from a\"))")
    write(tmp_path, "b", "(defrule (true) => (up-chat \"from b\"))")
    rules = rules_of(tmp_path, '(load-random 0 "a" "b")')
    assert len(rules) == 1 and rules[0].actions[0][1] == "from b"


def test_a_constant_gives_the_percent(tmp_path):
    write(tmp_path, "a", "(defrule (true) => (up-chat \"from a\"))")
    write(tmp_path, "b", "(defrule (true) => (up-chat \"from b\"))")
    rules = rules_of(tmp_path, '(defconst p 100)(load-random +p "a" "b")')
    assert rules[0].actions[0][1] == "from a"


def test_the_same_seed_gives_the_same_file(tmp_path):
    write(tmp_path, "a", "(defrule (true) => (up-chat \"from a\"))")
    write(tmp_path, "b", "(defrule (true) => (up-chat \"from b\"))")
    text = '(load-random 50 "a" "b")'
    picks = [rules_of(tmp_path, text, seed=7)[0].actions[0][1] for _ in range(3)]
    assert len(set(picks)) == 1


def test_an_unknown_file_gives_the_error_of_load(tmp_path):
    write(tmp_path, "a", "(defrule (true) => (up-chat \"from a\"))")
    with pytest.raises(ValueError, match="no file"):
        rules_of(tmp_path, '(load-random 100 "missing")')
