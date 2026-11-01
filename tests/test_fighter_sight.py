"""Each unit of the mob kinds of the stance check gets a sight (#5555): #5338 took the armor classes of Alfred the
Alpaca and the War Penguin away, so combat.sight_command gave them none and they did not attack in their range."""
from test_stances_kinds import KINDS, NO_RETURN

from game import combat


def test_each_fighting_kind_gets_a_sight():
    assert not [n for n in KINDS.values() if n not in NO_RETURN and combat.sight_command("u", n, 4) is None]
