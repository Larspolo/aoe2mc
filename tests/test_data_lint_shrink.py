"""`tools/data_lint.py --shrink` lowers the counts of its list and keeps the other lines (#3066): it read the list after
the open with mode "w" had emptied it."""
import data_lint


def test_shrink_lowers_the_count_and_keeps_the_line(tmp_path, monkeypatch):
    path = tmp_path / "list.txt"
    path.write_text(data_lint.HEAD + "mod.py:f 2\nother.py:g 1\n", encoding="utf-8")
    monkeypatch.setattr(data_lint, "LIST", str(path))
    monkeypatch.setattr(data_lint, "scan", lambda: {"mod.py:f": [(3, ["NAME"])]})
    assert data_lint.main(["--shrink"]) == 0
    assert path.read_text(encoding="utf-8") == data_lint.HEAD + "mod.py:f 1\n"
