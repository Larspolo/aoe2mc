import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework" / "tools"))
import dashboard  # noqa: E402


def test_a_list_item_names_a_dependency():
    body = "## Context\n- Part of #1.\n- Depends on: #5758 (the selection).\n"
    assert dashboard.depends({"body": body}) == [5758]


def test_a_dependency_in_text_is_not_one():
    assert dashboard.depends({"body": "It depends. Text Depends on: #3 here.\n"}) == []
