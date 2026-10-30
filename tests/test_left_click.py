"""game/gather.py: on Paper a left click with the command stick selects the own unit under the look and places the
chosen building, as in AoE2 (#4703). A left click on the ground still clears the selection (#1788)."""
import math

from game import gather

from test_deselect import paper


def left(server, g, at, look):
    """Steve stands at block `at`, looks at block `look` and left clicks (the score of AoePlugin.onLeftClick)."""
    eye = (at[0], 64.0, at[1])
    dx, dz, dy = look[0] - eye[0], look[1] - eye[2], 1 - 1.62
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": eye, "Rotation": (yaw, pitch)}
    server.scores[gather.LEFT] = 1
    server.log.clear()
    return g.clicks()


def test_a_left_click_on_an_own_unit_selects_it():
    server, g = paper()
    assert left(server, g, (5.5, 13.5), (5.5, 10.5)) == []             # no right click: no order
    assert g.selected == {"m-1"} and gather.LEFT not in server.scores


def test_a_left_click_on_another_unit_changes_the_selection():
    server, g = paper()
    g.select("v-1")
    left(server, g, (5.5, 13.5), (5.5, 10.5))
    assert g.selected == {"m-1"}


def test_a_left_click_on_the_ground_clears_the_selection():
    server, g = paper()
    g.select("m-1")
    left(server, g, (20.5, 30.5), (20.5, 27.5))
    assert g.selected == set()


def test_a_left_click_places_the_chosen_building(monkeypatch):
    server, g = paper()
    placed = []
    monkeypatch.setattr(gather.build, "chosen", lambda g, name: "HOUSE")   # gather imports it by its plain name
    monkeypatch.setattr(g, "place", lambda name, b, eye, d: placed.append((name, b)))
    left(server, g, (20.5, 30.5), (20.5, 27.5))
    assert placed == [("Steve", "HOUSE")]
