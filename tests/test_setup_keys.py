"""Each key of game/data/setup.jsonl has one line in game/data/setup_keys.jsonl (#2558): its type, what it does, its
issue. A new game mode or lobby setting then adds a line there, not a key to the shared lines of check_setup()."""
import pytest
from data_checks.setup import check as check_setup


def test_a_key_with_no_line_in_setup_keys_fails():
    with pytest.raises(AssertionError, match="setup_keys.jsonl"):
        check_setup({"name": "x", "ages": 1, "new_key": 1})


def test_a_key_of_the_wrong_type_fails_and_a_known_key_passes():
    check_setup({"name": "x", "ages": 1, "note": "n"})
    with pytest.raises(AssertionError):
        check_setup({"name": "x", "ages": "1"})


def test_a_line_has_exactly_one_key_of_a_kind():
    with pytest.raises(AssertionError):
        check_setup({"name": "x", "ages": 1, "level": "ultra"})
    with pytest.raises(AssertionError):
        check_setup({"name": "x", "note": "n"})
