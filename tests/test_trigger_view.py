"""Timer triggers move the view (the player) of a player to a tile (#2610)."""
import numpy as np

import aoe2mc


def effect(tile=(3, 5), player=1):
    return dict(type=aoe2mc.CHANGE_VIEW, message="", player=player, time=0, object=None, tile=list(tile),
                area=[-1] * 4)


def lines(effects, T=4):
    trig = dict(id=7, name="t", enabled=True, looping=False, effects=effects,
                conditions=[dict(type=aoe2mc.TIMER, timer=30, inverted=False)])
    files = aoe2mc.trigger_files([trig], T, np.full((64, 64), 70, np.int16))[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_change_view_moves_the_players_of_the_team_to_the_middle_of_the_tile():
    assert lines([effect()]) == ["tp @a[team=p1] 14.5 70 22.5"]


def test_gaia_or_no_player_moves_all_players():
    assert lines([effect(player=0)]) == lines([effect(player=-1)]) == ["tp @a 14.5 70 22.5"]


def test_no_tile_or_a_tile_outside_the_map_gives_no_line():
    for e in (effect(tile=(-1, -1)), effect(tile=(40, 5))):
        assert lines([e]) == []
