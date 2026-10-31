"""The lang files of the game program texts in the resource pack (#5345)."""
import json
import zipfile

import aoe2mc


def _pack(out, **kw):
    aoe2mc.write_resourcepack(str(out), **kw)
    return out / "resourcepacks" / "resources.zip"


def test_en_us_lang_file_has_each_text(tmp_path):
    rows = [json.loads(s) for s in open(aoe2mc.TEXTS, encoding="utf-8") if s.strip()]
    a, b = _pack(tmp_path / "a"), _pack(tmp_path / "b")
    with zipfile.ZipFile(a) as z:
        lang = json.loads(z.read("assets/aoe2mc/lang/en_us.json"))
    assert {r["name"]: r["en_us"] for r in rows}.items() <= lang.items()   # and the data texts (#5377)
    assert a.read_bytes() == b.read_bytes()


def test_second_code_gives_second_lang_file(tmp_path):
    data = tmp_path / "texts.jsonl"
    data.write_text('{"name": "aoe2mc.x", "en_us": "Victory", "de_de": "Sieg"}\n{"name": "aoe2mc.y", "en_us": "Defeat"}\n')
    with zipfile.ZipFile(_pack(tmp_path / "w", texts=str(data))) as z:
        names = {n for n in z.namelist() if "/lang/" in n}
        assert names == {"assets/aoe2mc/lang/en_us.json", "assets/aoe2mc/lang/de_de.json"}
        assert json.loads(z.read("assets/aoe2mc/lang/de_de.json")) == {"aoe2mc.x": "Sieg"}
