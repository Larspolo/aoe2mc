"""game/gather.py: on Paper the player holds the right click with the wand to draw the selection box (#992, choice A)."""
import json

from test_gather_attack import click
from test_lang_orders import plain_log
from test_select_type import setup

from game import hints, lang


def drag():
    server, g = setup()
    g.paper, now = True, [0.0]
    g.clock = lambda: now[0]
    return server, g, now


def use(server, g, at, look):
    g.wands.add("Steve")                                               # clicks() saw the wand statistic
    return click(server, g, at, look)


def test_a_held_right_click_selects_the_box_at_the_release():
    server, g, now = drag()
    use(server, g, (2.5, 2.5), (2.5, 8.5))
    first = g.corners["Steve"]
    assert g.holds == {"Steve": 0.0} and hints.state(g, "Steve")[0] == "drag"
    assert any(c.startswith("aoe box Steve ") for c in plain_log(server.log))
    for t in (0.2, 0.4, 0.6):                                          # the held button: a use each 4 ticks
        now[0] = t
        use(server, g, (10.5, 24.5), (10.5, 18.5))
        assert g.corners["Steve"] == first and not g.selected
    now[0] = 0.8
    g.release()
    assert g.holds == {"Steve": 0.6} and not g.selected                # 0.2 s without a use: still held
    now[0] = 1.2
    server.log.clear()
    g.release()
    assert not g.holds and not g.corners and "aoe box-clear Steve" in server.log
    assert g.selected == {"m-1", "m-2", "m-3", "a-1"}                  # the box of the press and the release cells


def test_a_release_on_the_first_corner_cancels_the_box():
    server, g, now = drag()
    g.select("v-1")
    use(server, g, (2.5, 2.5), (2.5, 8.5))
    now[0] = 1.0
    server.log.clear()
    g.release()
    assert not g.holds and not g.corners and g.selected == {"v-1"}
    assert "aoe box-clear Steve" in server.log
    assert 'title Steve actionbar ' + json.dumps(lang.text("aoe2mc.gather.box_cancelled")) in server.log


def test_clicks_releases_a_drag_also_without_a_use():
    server, g, now = drag()
    use(server, g, (2.5, 2.5), (2.5, 8.5))
    now[0] = 1.0
    assert g.clicks() == [] and not g.holds and not g.corners


def test_vanilla_keeps_two_clicks():
    server, g = setup()
    use(server, g, (2.5, 2.5), (2.5, 8.5))
    assert not g.holds and "Steve" in g.corners and hints.state(g, "Steve")[0] == "corner"
    use(server, g, (10.5, 24.5), (10.5, 18.5))
    assert not g.corners and g.selected == {"m-1", "m-2", "m-3", "a-1"}
