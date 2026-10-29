"""game/gather.py: an order of the person plays one order voice of the first selected unit (#3500, sounds.jsonl)."""
import math

from game import gather

from test_gather import FakeServer, grid
from test_gather_attack import click


def setup():
    """Three villagers and a knight of player 1, an enemy militia of player 2, open ground."""
    feet = {"v-1": (5.5, 64.0, 5.5), "v-2": (6.5, 64.0, 5.5), "v-3": (7.5, 64.0, 5.5), "k-1": (9.5, 64.0, 14.5),
            "e-1": (20.5, 64.0, 14.5)}
    names = {"v-1": ("VILLAGER_MALE", 1), "v-2": ("VILLAGER_MALE", 1), "v-3": ("VILLAGER_FEMALE", 1),
             "k-1": ("KNIGHT", 1), "e-1": ("MILITIA", 2)}
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [0.5, 0.5]} for u, (n, p) in names.items()]
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    return server, gather.Gather(server, grid([[64] * 40 for _ in range(40)], objects)).setup()


def sounds(log, cls=None):
    return [c for c in log if c.startswith("playsound ")
            and (cls is None or c.startswith(f"playsound minecraft:{gather.VOICES[cls]['order']} voice "))]


def walk(server, g, at, cell):
    """Steve stands at block `at` (x, z) and clicks the ground cell: the move order."""
    eye = (at[0], 65.62, at[1])
    dx, dz, dy = cell[0] + 0.5 - eye[0], cell[1] + 0.5 - eye[2], 64.0 - eye[1]
    server.entities["Steve"] = {"Pos": (at[0], 64.0, at[1]),
                                "Rotation": (math.degrees(math.atan2(-dx, dz)), -math.degrees(math.atan2(dy, math.hypot(dx, dz))))}
    server.log.clear()
    g.click("Steve")
    return server.log


def test_a_move_order_of_three_villagers_plays_one_order_voice():
    server, g = setup()
    g.choose({"v-1", "v-2", "v-3"}, "v-1")
    log = walk(server, g, (6.5, 9.5), (6, 13))
    assert len(sounds(log)) == 1 and len(sounds(log, "villager")) == 1


def test_an_attack_order_of_a_knight_plays_the_cavalry_order_voice():
    server, g = setup()
    g.choose({"k-1"}, "k-1")
    log = click(server, g, (17.5, 14.5), (20.5, 14.5))
    assert any(c.startswith("aoe attack") for c in log)
    assert len(sounds(log)) == 1 and len(sounds(log, "cavalry")) == 1


def test_an_order_of_the_game_program_plays_no_voice():
    server, g = setup()
    g.choose({"v-1"}, "v-1")
    server.log.clear()
    g.walk_to("Steve", (6, 13), {"v-2"})                               # as next_task and a rally point do: units given
    g.build({"footprint": [20, 22, 20, 22], "progress": 0, "name": "HOUSE", "player": 1}, {"v-3"})
    assert not sounds(server.log)
