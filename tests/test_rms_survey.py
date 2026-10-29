import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rms_survey  # noqa: E402


def test_survey_lists_unread_commands(tmp_path, capsys, monkeypatch):
    (tmp_path / "a_plain.rms").write_text("<LAND_GENERATION>\nbase_terrain GRASS\n", encoding="utf-8")
    (tmp_path / "b_unknown.rms").write_text("<LAND_GENERATION>\nunknown_command 3\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["rms_survey.py", str(tmp_path)])
    rms_survey.main()
    out = capsys.readouterr().out
    assert "| a_plain | 0 | ok |" in out
    assert "| b_unknown | 1 | unknown_command is not read yet |" in out
    assert "| unknown_command is not read yet | 1 |" in out


def test_survey_goes_on_after_an_error(tmp_path, capsys, monkeypatch):
    (tmp_path / "a_broken.rms").write_text("<LAND_GENERATION>\nboom\n", encoding="utf-8")
    (tmp_path / "b_plain.rms").write_text("<LAND_GENERATION>\nbase_terrain GRASS\n", encoding="utf-8")
    real = rms_survey.rmap.generate

    def generate(text, seed, **kw):
        if "boom" in text:
            raise ValueError("boom")
        return real(text, seed, **kw)

    monkeypatch.setattr(rms_survey.rmap, "generate", generate)
    monkeypatch.setattr(sys, "argv", ["rms_survey.py", str(tmp_path)])
    rms_survey.main()
    out = capsys.readouterr().out
    assert "| a_broken | 0 | error: ValueError: boom |" in out
    assert "| b_plain | 0 | ok |" in out
