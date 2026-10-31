"""game/gather.py: on Paper a held right click of the command stick draws the selection box, a short one clicks as
before (#1786, owner feedback in a demo). The first use of a hold waits HOLD seconds: a hold never gives an order."""
import math

from test_select_type import setup

from game import gather, hints


def paper():
    server, g = setup()
    g.paper, now = True, [0.0]
    g.clock = lambda: now[0]
    return server, g, now


def look(server, at, to, y=0):
    """Steve stands at block `at` and looks at block `to` on the ground (y = 1: at the body of a unit there)."""
    eye = (at[0], 64.0, at[1])
    dx, dz, dy = to[0] - eye[0], to[1] - eye[2], y - 1.62
    server.entities["Steve"] = {"Pos": eye, "Rotation": (math.degrees(math.atan2(-dx, dz)),
                                                         -math.degrees(math.atan2(dy, math.hypot(dx, dz))))}


def use(server, g, uses=1):
    """The stick statistic counts uses since the last call; clicks() reads it and returns the players to click now."""
    server.scores["aoe_use"] = uses
    server.log.clear()
    return g.clicks()


def test_a_short_click_waits_one_use_period_and_keeps_its_look():
    server, g, now = paper()
    look(server, (5.5, 13.5), (5.5, 10.5), y=1)                        # the militia m-1
    assert use(server, g) == [] and not g.selected and "Steve" in g.pending
    now[0] = gather.HOLD / 2
    assert g.clicks() == []                                            # no next use yet, but in the time
    now[0] = gather.HOLD
    look(server, (5.5, 13.5), (30.5, 30.5))                            # the look moved after the click
    assert g.clicks() == ["Steve"] and not g.pending
    g.click("Steve")
    assert g.selected == {"m-1"} and not g.corners and not g.holds


def test_a_held_click_draws_the_box_from_the_first_cell():
    server, g, now = paper()
    g.select("v-1")
    look(server, (2.5, 2.5), (2.5, 8.5))
    assert use(server, g) == [] and any(c.startswith("aoe box Steve 2 8 ") for c in server.log)   # at once (#3268)
    look(server, (2.5, 2.5), (10.5, 18.5))
    now[0] = 0.2                                                       # the next use of the held button
    assert use(server, g) == [] and g.holds == {"Steve": 0.2} and g.corners["Steve"] == (2, 8)
    assert hints.state(g, "Steve")[0] == "drag"
    for t in (0.4, 0.6):
        now[0] = t
        assert use(server, g) == [] and g.holds == {"Steve": t}
    assert g.selected == {"v-1"}                                       # no click and no order during the hold
    assert not any(c.startswith(("aoe moveto", "aoe attack")) for c in server.log)
    now[0] = 1.2
    assert g.clicks() == [] and not g.holds and not g.corners
    assert g.selected == {"m-1", "m-2", "m-3", "a-1"}                  # military units win, as Gather.box


def test_two_uses_in_one_call_are_a_hold():
    server, g, now = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    assert use(server, g, uses=2) == [] and "Steve" in g.holds and not g.pending


def test_a_hold_on_a_selected_villager_opens_no_menu():
    server, g, now = paper()
    g.select("v-1")
    look(server, (12.5, 1.5), (12.5, 4.5))
    use(server, g)
    now[0] = 0.2
    use(server, g)
    assert "Steve" not in g.menus and "Steve" in g.holds


def test_a_release_on_the_start_cell_cancels_the_box():
    server, g, now = paper()
    g.select("v-1")
    look(server, (2.5, 2.5), (2.5, 8.5))
    use(server, g)
    now[0] = 0.2
    use(server, g)
    now[0] = 1.0
    server.log.clear()
    assert g.clicks() == [] and not g.holds and not g.corners and g.selected == {"v-1"}
    assert 'title Steve actionbar {"text": "Selection box: cancelled"}' in server.log


def test_an_empty_box_clears_the_selection():
    server, g, now = paper()
    g.select("m-1")
    look(server, (25.5, 25.5), (25.5, 30.5))
    use(server, g)
    look(server, (25.5, 25.5), (30.5, 35.5))
    now[0] = 0.2
    use(server, g)
    now[0] = 1.0
    g.clicks()
    assert g.selected == set()


def test_paper_gives_no_wand_and_vanilla_keeps_it():
    server, g, _ = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    use(server, g)
    assert not any(gather.WAND in c and "give" in c for c in server.log)
    server, g = setup()
    server.scores["aoe_use"] = 1
    assert g.clicks() == ["Steve"]                                     # vanilla: a stick use clicks at once
    assert any(f"give @s minecraft:{gather.WAND}" in c for c in server.log)


def test_the_hint_names_the_hold_on_paper():
    _, g, _ = paper()
    assert hints.state(g) == ("none", hints.TEXTS["none"])
    _, g = setup()
    assert hints.state(g) == ("none", hints.TEXTS["none-wand"])


def test_a_chosen_building_places_at_once(monkeypatch):
    server, g, now = paper()
    monkeypatch.setattr(gather.build, "chosen", lambda g, name: "HOUSE")
    look(server, (2.5, 2.5), (2.5, 8.5))
    assert use(server, g) == ["Steve"] and not g.pending               # no box while a foundation waits
