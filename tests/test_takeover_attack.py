"""The bot of a takeover says the attack time of the save, not the --bot-attack default (#5626)."""
import math

import run


def test_saved_attack_wins():
    state = {"players": {"2": {"bot": {"attack": 420.0}}}}
    assert run.saved_attack(state, 2, 600.0) == 420.0


def test_no_save_keeps_option():
    assert run.saved_attack(None, 2, 600.0) == 600.0
    assert run.saved_attack({"players": {"2": {}}}, 2, 600.0) == 600.0


def test_never_stays_never():
    assert run.saved_attack({"players": {"2": {"bot": {"attack": 420.0}}}}, 2, math.inf) == math.inf
