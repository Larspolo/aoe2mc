"""Each string of each language of the lang files has the %s count of its en_us string (#5436)."""
import json

import aoe2mc


def test_each_language_keeps_the_arguments():
    files = {k: json.loads(v) for k, v in aoe2mc.lang_files().items()}
    en = files.pop("assets/aoe2mc/lang/en_us.json")
    assert files                                                   # at least one translation
    for path, texts in files.items():
        for key, s in texts.items():
            assert s.count("%s") == en[key].count("%s"), (path, key)


def test_translation_columns_of_the_step_texts(tmp_path):
    (tmp_path / "texts.jsonl").write_text('{"name": "aoe2mc.a", "en_us": "A %s", "xx_yy": "B %s"}\n')
    (tmp_path / "tutorial.jsonl").write_text('{"name": "s", "text": "T", "text_xx_yy": "U", "tip": "P"}\n')
    (tmp_path / "challenges.jsonl").write_text('{"name": "c", "goal": "G", "goal_xx_yy": "H"}\n')
    p = str(tmp_path / "texts.jsonl")
    old, aoe2mc.TEXTS = aoe2mc.TEXTS, p
    try:
        files = {k: json.loads(v) for k, v in aoe2mc.lang_files(p).items()}
    finally:
        aoe2mc.TEXTS = old
    assert files["assets/aoe2mc/lang/xx_yy.json"] == {"aoe2mc.a": "B %s", "aoe2mc.tutorial.s": "U", "aoe2mc.challenge.c": "H"}
    assert files["assets/aoe2mc/lang/en_us.json"]["aoe2mc.tutorial.tip_s"] == "P"
