"""tools/ship_pr.py stops a change of data files only that adds or changes a test: such a test checks the content of
the data (owner, 2026-10-29, #4242)."""
import ship_pr as ship


def test_a_data_change_with_a_test_stops():
    changed = ["game/data/train.jsonl", "tests/test_new.py"]
    assert ship.data_only_tests(changed) == ["tests/test_new.py"]
    assert ship.data_only_tests(["data/lines.jsonl", "docs/x.md", "tests/test_a.py"]) == ["tests/test_a.py"]


def test_a_code_change_or_a_data_change_alone_passes():
    assert not ship.data_only_tests(["game/data/train.jsonl", "game/train.py", "tests/test_new.py"])
    assert not ship.data_only_tests(["game/data/train.jsonl", "docs/extend.md"])
    assert not ship.data_only_tests(["tests/test_new.py"])                    # a test-only change
