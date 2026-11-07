"""A "Depends on:" item after the end of a sentence on the same line holds the ticket (#6067): #6032 and #6039 said
`Part of #E. Depends on: ...`, the pick list offered them with open dependencies, and two runs gave them back."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "framework" / "tools"))
import dashboard  # noqa: E402


def test_an_item_after_a_sentence_names_its_dependencies():
    body = "## Context\nPart of #6027. Depends on: #6028, #6029, #6030.\n"
    assert dashboard.depends({"body": body}) == [6028, 6029, 6030]


def test_an_item_in_a_list_after_a_sentence_counts_too():
    assert dashboard.depends({"body": "- Part of #6033. Depends on: #6035 (the cliffs).\n"}) == [6035]


def test_a_mention_inside_a_sentence_is_no_dependency():
    assert dashboard.depends({"body": "The line Depends on: #3 is the form.\n"}) == []
