"""game/per.py: up-send-flare with a goal pair that has no point puts no flare and raises no error (#5095). The airef
example: up-get-point position-target finds no target, then up-send-flare sends at the pair."""
from test_per_up_flares import script


def test_send_flare_with_no_point_puts_no_flare():
    s, b, me = script("(up-get-point position-target gl-point-x) (up-send-flare gl-point-x)")
    s.step()
    assert not getattr(b.g, "flares", [])                          # no point: no flare (the list starts at the first flare)
    assert all(isinstance(s.goals[k], int) for k in (100, 101))    # the pair keeps numbers (airef: -1 for no point)
