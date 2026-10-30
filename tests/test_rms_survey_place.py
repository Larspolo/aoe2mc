import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rms_survey  # noqa: E402


def run_survey(tmp_path, capsys, monkeypatch, error):
    (tmp_path / "a_broken.rms").write_text("<LAND_GENERATION>\nboom\n", encoding="utf-8")

    def generate(text, seed, **kw):
        raise error

    monkeypatch.setattr(rms_survey.rmap, "generate", generate)
    monkeypatch.setattr(sys, "argv", ["rms_survey.py", str(tmp_path)])
    rms_survey.main()
    return capsys.readouterr().out


def test_python_error_shows_its_place(tmp_path, capsys, monkeypatch):
    out = run_survey(tmp_path, capsys, monkeypatch, IndexError("list index out of range"))
    assert "| a_broken | 0 | error: IndexError: list index out of range (at " in out


def test_rms_error_shows_no_place(tmp_path, capsys, monkeypatch):
    out = run_survey(tmp_path, capsys, monkeypatch, rms_survey.rmap.RmsError("x"))
    assert "| a_broken | 0 | error: RmsError: x |" in out
    assert "(at " not in out
