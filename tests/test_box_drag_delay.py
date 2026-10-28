"""game/gather.py: the held right click sets corner 1 of the selection box on the first use, with no wait for the
next use (#3268, owner feedback: "I have to hold it, wait a bit, and only then drag")."""
from game import gather

from test_select_hold import look, paper, use


def test_the_first_use_sets_corner_1_at_once():
    server, g, now = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    assert use(server, g) == [] and g.corners["Steve"] == (2, 8)
    assert any(c.startswith("aoe box Steve 2 8 ") for c in server.log)


def test_the_drag_keeps_corner_1_and_selects_in_the_same_second():
    server, g, now = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    use(server, g)
    look(server, (2.5, 2.5), (10.5, 18.5))
    now[0] = 0.2
    use(server, g)
    assert g.corners["Steve"] == (2, 8) and "Steve" in g.holds
    now[0] = 0.2 + gather.RELEASE + 0.05
    g.clicks()
    assert g.selected == {"m-1", "m-2", "m-3", "a-1"}


def test_a_short_click_clears_the_box():
    server, g, now = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    use(server, g)
    now[0] = gather.HOLD
    server.log.clear()
    assert g.clicks() == ["Steve"] and not g.corners and "aoe box-clear Steve" in server.log
