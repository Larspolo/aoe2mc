"""framework/tools/ship_pr.py data_only_tests: the quick CI fails a change that adds or changes a test of data files only
(owner, 2026-10-29, #4353; the step "Data-only change adds no test" of ci.yml)."""
import sys

sys.path.insert(0, "tools")
import ship_pr  # noqa: E402


def test_data_and_a_test_fail():
    changed = ["game/data/train.jsonl", "tests/test_techs_new.py"]
    assert ship_pr.data_only_tests(changed) == ["tests/test_techs_new.py"]


def test_data_code_and_a_test_pass():
    changed = ["game/data/train.jsonl", "game/garrison.py", "tests/test_techs_new.py"]
    assert ship_pr.data_only_tests(changed) == []


def test_data_and_docs_with_a_test_fail():
    changed = ["game/data/train.jsonl", "docs/extend.md", "tests/test_x.py"]
    assert ship_pr.data_only_tests(changed) == ["tests/test_x.py"]


def test_a_test_alone_or_data_alone_pass():
    assert ship_pr.data_only_tests(["tests/test_x.py"]) == []
    assert ship_pr.data_only_tests(["game/data/train.jsonl"]) == []
