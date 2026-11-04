"""game/export.py: the units of a player with no game loop stay in the export (#5752)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import export  # noqa: E402


def unit(uuid, player):
    return {"kind": "unit", "id": 83, "player": player, "uuid": uuid, "tile": (2.0, 3.0)}


def test_a_player_not_in_the_save_keeps_its_units_and_a_dead_unit_of_a_saved_player_goes():
    data = {"tile_size": 4, "map_size": 10, "objects": [unit("a", 1), unit("b", 1), unit("c", 2), unit("d", 2)]}
    state = {"players": {"1": {"villagers": {"a": {}}}}}
    pos = {"a": (8.0, 12.0), "c": (16.0, 20.0)}                        # "d" has no entity in the world
    out = export.objects(data, state, pos)
    assert sorted((o["player"], o["tile"]) for o in out) == [(1, (2.0, 3.0)), (2, (4.0, 5.0))], out
