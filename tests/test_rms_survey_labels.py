import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rms_survey  # noqa: E402


def test_undefined_labels_count_the_maps_that_test_them(tmp_path):
    (tmp_path / "a_first.rms").write_text("#define MY_LAND\nif REGICIDE\nbase_terrain GRASS\nendif\n", encoding="utf-8")
    (tmp_path / "b_second.rms").write_text("if REGICIDE\nelseif LUDIKRIS_MAP\nendif\n", encoding="utf-8")
    maps = rms_survey.undefined(str(tmp_path))
    assert maps["REGICIDE"] == 2
    assert maps["LUDIKRIS_MAP"] == 1
    assert "MY_LAND" not in maps
