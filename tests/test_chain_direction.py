"""The tile direction of each AoE2 chain object (#3102)."""
import buildings


def test_chain_directions():
    """Decision A of #3101: the line reading of the names; AoE2 DE CHAIN 1396 is long along tile x, 1397 along tile y."""
    assert buildings.CHAIN_DIRECTION == {"NORTH_TO_SOUTH": (1, -1), "NORTHWEST_TO_SOUTHEAST": (0, 1),
                                         "SOUTHWEST_TO_NORTHEAST": (1, 0), "WEST_TO_EAST": (1, 1)}


def test_names_match_one_direction():
    """NORTHWEST_TO_SOUTHEAST must not match the WEST_TO_EAST key by its end, or the order of the table decides."""
    for name in buildings.CHAIN_DIRECTION:
        assert [k for k in buildings.CHAIN_DIRECTION if f"CHAIN_{name}".endswith(k)] == [name]
