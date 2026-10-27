"""The enemy buildings on the live minimap of a view player (#1678): only the ones that it or an ally saw, in the
last seen state. Fake RCON."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, build, data  # noqa: E402
from test_replay_delete import delete  # noqa: E402

T = 4


def mob(uuid, player, x, y):
    return types.SimpleNamespace(uuid=uuid, player=player, name="VILLAGER_MALE", pos=(x * T, 70.0, y * T))


def minimap(cmds):
    return [c for c in cmds if c.startswith("aoe minimap building") or c.startswith("aoe minimap unbuild")]


def view(pov=1):
    """A 32 x 32 tile map: a villager of player 1 at tile (5, 5), a house of player 2 at tile (25, 25)."""
    d = data([], n=128)
    d["players"]["2"]["arch"] = "western"                               # "meso" is not in buildings.ARCH
    r = replay.Replay(Fake(), d, ai=True)
    r.pov = pov
    out = minimap(r.commands(build(tile=(25.0, 25.0), player=2)))
    r.units = {1: mob("u1", 1, 5.5, 5.5), 2: mob("u2", 2, 20.5, 20.5)}   # after the build: it pushes units out
    return r, out, r.placed[-1][2]


def test_an_enemy_building_shows_only_when_it_comes_into_sight():
    r, built, (x0, x1, z0, z1) = view()
    assert built == [] and minimap(r.fog()) == []                       # far out of the sight of the villager
    r.units[1].pos = (23.5 * T, 70.0, 23.5 * T)                         # the villager walks to it
    assert minimap(r.fog()) == [f"aoe minimap building {x0} {z0} {x1} {z1} p2"]
    assert minimap(r.fog()) == []                                       # only the changes


def test_a_building_that_dies_out_of_sight_stays_until_its_place_is_in_sight():
    r, _, (x0, _, z0, _) = view()
    r.units[1].pos = (23.5 * T, 70.0, 23.5 * T)
    r.fog()
    r.units[1].pos = (5.5 * T, 70.0, 5.5 * T)                           # back home: the house is out of sight
    r.fog()
    assert minimap(r.commands(delete(500, [900], names=["HOUSE"], player=2))) == []
    assert not r.placed and minimap(r.fog()) == []                     # the last seen state: still there
    r.units[1].pos = (23.5 * T, 70.0, 23.5 * T)
    assert minimap(r.fog()) == [f"aoe minimap unbuild {x0} {z0}"]


def test_the_own_and_allied_buildings_show_and_no_view_player_shows_all():
    r, _, (x0, x1, z0, z1) = view(pov=2)                               # the house is of the view player
    assert minimap(r.fog()) == [f"aoe minimap building {x0} {z0} {x1} {z1} p2"]
    r, _, rect = view()
    r.data["players"]["1"]["team"] = r.data["players"]["2"]["team"] = 1
    assert minimap(r.fog()) == [f"aoe minimap building {x0} {z0} {x1} {z1} p2"]    # an ally shares it
    r, _, rect = view()
    r.fog()
    r.pov = None                                                        # no view player: all buildings again
    assert minimap(r.fog()) == [f"aoe minimap building {x0} {z0} {x1} {z1} p2"]
    assert minimap(r.commands(delete(500, [900], names=["HOUSE"], player=2))) == [f"aoe minimap unbuild {x0} {z0}"]


def test_a_new_view_player_draws_its_own_set():
    r, _, (x0, _, z0, _) = view()
    r.pov = 2
    r.fog()
    r.pov = 1                                                           # player 1 never saw the house
    assert minimap(r.fog()) == [f"aoe minimap unbuild {x0} {z0}"]
