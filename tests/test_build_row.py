"""game/build.py: a sneak right click (Shift) places a foundation and keeps the chosen building, so a player places
a row of foundations, and the selected villagers build them in the order of the clicks (#1805). Fake server."""
from test_build_at_once import line_map
from test_lang_orders import plain_log

from game import build, hints, lang


def click(server, g, x, sneak, name="HOUSE"):
    """Click the ground under the block (x, 9) with name chosen; the menu choice stays from the last click."""
    server.chosen = server.chosen or build.MENU.index(name) + 1
    server.sneak = sneak
    server.entities["Steve"]["Pos"] = (x + 0.5, 64.0, 9.5)
    g.click("Steve")


def sneaking(server):
    """The fake server answers the is_sneaking predicate with server.sneak."""
    command = server.command

    def answer(cmd):
        if cmd == f"execute as Steve if predicate {build.SNEAK}":
            return "Test passed" if server.sneak else "Test failed"
        return command(cmd)
    server.command = answer


def test_two_sneak_clicks_and_one_click_give_three_sites_built_in_click_order():
    server, g = line_map()
    sneaking(server)
    g.stock["wood"] = 3 * build.price(g, "HOUSE")["wood"]
    click(server, g, 9, True)
    assert len(g.sites) == 1 and server.chosen                         # the choice stays
    click(server, g, 21, True)
    assert len(g.sites) == 2 and server.chosen
    click(server, g, 33, False)
    assert len(g.sites) == 3 and not server.chosen                     # a normal click ends the choice
    assert [s["footprint"][0] for s in g.sites] == [4, 16, 28] and g.stock["wood"] == 0
    first = g.sites[0]
    assert all(v.site is first and v.state == "to_site" for v in g.villagers.values())
    done = []
    for _ in range(6000):
        g.step()
        done += [i for i, s in enumerate(g.sites) if s["progress"] >= 1 and i not in done]
        if len(done) == 3:
            break
    assert done == [0, 1, 2]                                           # one after another, with no new click


def test_a_sneak_click_with_too_few_resources_says_so_and_keeps_the_choice():
    server, g = line_map()
    sneaking(server)
    g.stock["wood"] = build.price(g, "HOUSE")["wood"] + 5
    click(server, g, 9, True)
    click(server, g, 21, True)
    assert len(g.sites) == 1 and g.stock["wood"] == 5 and server.chosen
    assert any("Not enough resources" in c for c in plain_log(server.log))


def test_a_new_row_does_not_wait_for_the_sites_of_an_old_row():
    server, g = line_map()
    sneaking(server)
    click(server, g, 9, False)
    click(server, g, 21, False)
    assert all(v.site is g.sites[1] for v in g.villagers.values())    # two rows of one site each: the last order


def test_the_hint_of_a_chosen_building_names_the_shift_click():
    assert "Shift + right click: place more" in lang.plain(hints.hint("building", "House"))
