"""A translation is one file game/data/lang/<code>.jsonl with {"name", "text"} lines (#5901)."""
import json
import os

import aoe2mc


def test_lang_file_gives_its_language(tmp_path):
    (tmp_path / "texts.jsonl").write_text('{"name": "aoe2mc.a", "en_us": "A %s"}\n')
    (tmp_path / "tutorial.jsonl").write_text('{"name": "s", "text": "T"}\n')
    (tmp_path / "challenges.jsonl").write_text('{"name": "c", "goal": "G"}\n')
    (tmp_path / "lang").mkdir()
    (tmp_path / "lang" / "xx_yy.jsonl").write_text('{"name": "aoe2mc.a", "text": "B %s"}\n'
                                                   '{"name": "aoe2mc.tutorial.s", "text": "U"}\n')
    p = str(tmp_path / "texts.jsonl")
    old, aoe2mc.TEXTS = aoe2mc.TEXTS, p
    try:
        files = {k: json.loads(v) for k, v in aoe2mc.lang_files(p).items()}
    finally:
        aoe2mc.TEXTS = old
    assert files["assets/aoe2mc/lang/xx_yy.json"] == {"aoe2mc.a": "B %s", "aoe2mc.tutorial.s": "U"}
    assert files["assets/aoe2mc/lang/en_us.json"]["aoe2mc.a"] == "A %s"


def test_each_lang_file_line_has_an_english_key():
    en = json.loads(aoe2mc.lang_files()["assets/aoe2mc/lang/en_us.json"])
    folder = os.path.join(os.path.dirname(aoe2mc.TEXTS), "lang")
    for fn in sorted(os.listdir(folder)):
        rows = [json.loads(s) for s in open(os.path.join(folder, fn), encoding="utf-8") if s.strip()]
        assert all(set(r) == {"name", "text"} and r["name"] in en for r in rows), fn
        assert len({r["name"] for r in rows}) == len(rows), fn
