"""A script places PALISADE_WALL (object 72), as Hideout does with GNR_HIDEOUTWALL (#5711)."""
import rmap

SCRIPT = """<OBJECTS_GENERATION>
create_object PALISADE_WALL { number_of_objects 3 }
"""


def test_palisade_wall_is_placed_with_no_warning():
    notes = []
    out = rmap.generate(SCRIPT, 1, 2, warn=notes.append)
    assert not [m for m in notes if "PALISADE_WALL" in m]
    assert [o["name"] for o in out["objects"]] == ["PALISADE_WALL"] * 3
