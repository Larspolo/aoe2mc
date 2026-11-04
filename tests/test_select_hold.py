"""game/gather.py: on Paper the command stick draws no selection box with the right click: a right click gives its
order at once, and a held left click draws the box (#5759, before #1786). Vanilla keeps the wand."""
import math

from test_lang_orders import plain_log
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


def test_paper_gives_no_wand_and_vanilla_keeps_it():
    server, g, _ = paper()
    look(server, (2.5, 2.5), (2.5, 8.5))
    use(server, g)
    assert not any(gather.WAND in c and "give" in c for c in plain_log(server.log))
    server, g = setup()
    server.scores["aoe_use"] = 1
    assert g.clicks() == ["Steve"]                                     # vanilla: a stick use clicks at once
    assert any(f"give @s minecraft:{gather.WAND}" in c for c in plain_log(server.log))


def test_the_hint_names_the_hold_on_paper():
    _, g, _ = paper()
    assert hints.state(g) == ("none", hints.hint("none"))
    _, g = setup()
    assert hints.state(g) == ("none", hints.hint("none-wand"))


def test_a_chosen_building_places_at_once(monkeypatch):
    server, g, now = paper()
    monkeypatch.setattr(gather.build, "chosen", lambda g, name: "HOUSE")
    look(server, (2.5, 2.5), (2.5, 8.5))
    assert use(server, g) == ["Steve"] and not g.corners              # no box while a foundation waits
