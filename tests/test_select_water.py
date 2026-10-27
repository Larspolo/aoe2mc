"""game/gather.py: a corner of the selection box on the water is the water cell under the look (fleet.pick), so a box
over own ships on deep water selects them (#2060). Fake server, no Minecraft."""
import math

from test_dock_train import dock_map

from game import fleet

SHIPS = {"s-1": (17.5, 63.0, 6.5), "s-2": (20.5, 63.0, 9.5)}         # on the water (x >= 14), surface y 63


def aim(server, at, cell):
    """Steve stands on the land at block `at` and looks at the water surface of block cell."""
    eye = (at[0], 64.0, at[1])
    dx, dz, dy = cell[0] + 0.5 - eye[0], cell[1] + 0.5 - eye[2], 63 - (eye[1] + 1.62)
    yaw, pitch = math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz)))
    server.entities["Steve"] = {"Pos": eye, "Rotation": (yaw, pitch)}


def ships():
    server, g = dock_map()
    for u, pos in SHIPS.items():
        server.entities[u] = {"Pos": pos}
        g.soldiers[u] = "GALLEY"
    return server, g


def wand(server, g, cell):
    aim(server, (12.5, 12.5), cell)
    g.wands.add("Steve")                                               # clicks() saw the wand statistic
    g.click("Steve")


def test_the_corners_of_the_box_are_on_the_water_surface():
    server, g = ships()
    aim(server, (12.5, 12.5), (21, 3))
    look = g.look("Steve")
    assert g.map.pick_ground(*look) is None and fleet.pick(g, *look) == (21, 3)   # deep water up to the map edge
    wand(server, g, (16, 4))
    assert g.corners == {"Steve": (16, 4)}
    wand(server, g, (22, 11))
    assert g.selected == set(SHIPS) and not g.corners


def test_a_held_right_click_selects_the_ships_on_paper():
    server, g = ships()
    g.paper, now = True, [0.0]
    g.clock = lambda: now[0]
    wand(server, g, (16, 4))
    wand(server, g, (16, 4))                                           # the held button: a second use
    assert g.corners["Steve"] == (16, 4) and "Steve" in g.holds
    aim(server, (12.5, 12.5), (22, 11))
    now[0] = 1.0
    g.release()
    assert g.selected == set(SHIPS)
