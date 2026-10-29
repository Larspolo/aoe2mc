"""game/build.py: a sneak right click on an own construction site queues it for the selected builders, as the shift
queue of AoE2 (#3517). Fake server."""
from test_build_at_once import line_map
from test_build_row import click, sneaking


def site_click(server, g, x, sneak):
    """Click the site under the block (x, 9) with no building chosen."""
    server.chosen, server.sneak = 0, sneak
    server.entities["Steve"]["Pos"] = (x + 0.5, 64.0, 9.5)
    g.click("Steve")


def two_sites():
    """Site A at the block x 9 with the two villagers on it, site B at x 33 with no builders, no menu choice."""
    server, g = line_map()
    sneaking(server)
    click(server, g, 9, False)
    selected, g.selected = g.selected, set()
    click(server, g, 33, False)
    g.selected = selected
    a, b = g.sites
    assert all(v.site is a for v in g.villagers.values())
    return server, g, a, b


def test_a_sneak_click_on_a_site_queues_it_after_the_present_site():
    server, g, a, b = two_sites()
    site_click(server, g, 33, True)
    assert all(v.site is a for v in g.villagers.values())             # they stay on A
    for _ in range(6000):
        g.step()
        if a["progress"] >= 1:
            break
    assert a["progress"] >= 1 and b["progress"] < 1
    assert all(v.site is b for v in g.villagers.values())             # then on to B, with no new click
    for _ in range(6000):
        g.step()
        if b["progress"] >= 1:
            break
    assert b["progress"] >= 1


def test_a_click_without_sneak_sends_the_builders_to_the_site_at_once():
    server, g, a, b = two_sites()
    site_click(server, g, 33, False)
    assert a["progress"] < 1 and all(v.site is b for v in g.villagers.values())
