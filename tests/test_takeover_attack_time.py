"""The first bot attack after a takeover comes at --bot-attack, or ATTACK seconds after the takeover when later (#5632)."""
import types

import takeover


def attack(t, bot_attack="10:00"):
    r = types.SimpleNamespace(data={"players": {"1": {}, "2": {}}})
    return takeover.bot(r, 2, t * 1000, bot_attack=bot_attack)["attack"]


def test_takeover_at_5_waits_for_bot_attack():
    assert attack(300) == 600


def test_late_takeover_gives_time_to_play():
    assert attack(900) == 900 + takeover.ATTACK
    assert attack(300, "5:00") == 300 + takeover.ATTACK
