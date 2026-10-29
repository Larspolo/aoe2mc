"""framework/files.txt lists the generic files of the agent system (#4192)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import bootstrap  # noqa: E402


def test_each_file_once_and_real():
    paths = [p for p, _ in bootstrap.rows()]
    assert len(paths) == len(set(paths))
    assert [p for p in paths if not os.path.exists(os.path.join(ROOT, p))] == []
    assert "framework/files.txt" in bootstrap.generic(open(bootstrap.FILES).read())


def test_comments_blank_lines_and_globs():
    got = bootstrap.generic("# tools\n\ntools/claim.py\n  # more\ntests/test_framework_*.py\n")
    assert got == ["tools/claim.py", "tests/test_framework_files.py"]


def test_the_table_of_the_system_doc_holds_only_specific_files():
    assert {k for _, k in bootstrap.table(open(bootstrap.SYSTEM).read())} == {"specific"}
