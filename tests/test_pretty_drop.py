"""units.pretty of a name that is only a drop word (#4145): the build order of the replay showed "BARRACKS"."""
import units


def test_a_name_of_only_a_drop_word_is_capitalized():
    assert [units.pretty(n) for n in ("BARRACKS", "DONJON", "KREPOST", "STABLE")] == \
        ["Barracks", "Donjon", "Krepost", "Stable"]


def test_a_drop_word_next_to_other_parts_is_still_dropped():
    assert [units.pretty(n) for n in ("VILLAGER_FEMALE", "HOUSE_ANTIQUITY", "FISHING_SHIP_FULL")] == \
        ["Villager", "House", "Fishing Ship"]
