"""A Random Map record with a King for each player is a Regicide record (#4970). Fake match, no `mgz` needed."""
from types import SimpleNamespace as NS

import aoe2mc

KING = next(i for i, (_, name) in aoe2mc.object_kinds().items() if name == "KING")
HOUSE = next(i for i, (_, name) in aoe2mc.object_kinds().items() if name == "HOUSE")


def unit(object_id, x=1, y=1):
    return NS(object_id=object_id, position=NS(x=x, y=y), instance_id=object_id * 10 + x)


def match(kings_of, type_="Random Map"):
    """Two players; kings_of: the players that have a start King."""
    players = [NS(number=n, color_id=n - 1, civilization="BRITONS", position=NS(x=n, y=n), name=f"P{n}", profile_id=0,
                  objects=[unit(KING, n, n)] if n in kings_of else [unit(HOUSE, n, n)])
               for n in (1, 2)]
    tile = NS(position=NS(x=0, y=0), terrain=0, elevation=0)
    return NS(map=NS(dimension=4, tiles=[tile]), teams=[[players[0]], [players[1]]], players=players, gaia=[],
              type=type_, dataset="Definitive Edition", starting_age="Dark", population=200, all_technologies=False,
              map_reveal="Normal")


def lobby_type(m):
    return aoe2mc.read_record("unused.aoe2record", m)[4]["lobby"]["type"]


def test_a_king_for_each_player_makes_a_regicide_record():
    assert lobby_type(match({1, 2})) == "Regicide"


def test_a_king_for_one_player_only_stays_random_map():
    assert lobby_type(match({1})) == "Random Map"


def test_no_king_stays_random_map():
    assert lobby_type(match(set())) == "Random Map"


def test_a_king_for_each_player_keeps_other_modes():
    assert lobby_type(match({1, 2}, type_="Death Match")) == "Death Match"
