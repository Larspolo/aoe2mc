"""tools/aoe2_lang.py (#5435): the lang files of the names from the string tables of a local AoE2 DE install. The test
tables in tests/data/aoe2_strings have own texts, no AoE2 text."""
import json
import zipfile
from pathlib import Path

import aoe2_lang
import pytest

DATA = Path(__file__).resolve().parent / "data" / "aoe2_strings"
NAMES = {"aoe2mc.unit.TESTUNIT": "Testunit", "aoe2mc.unit.TEST_HALL": "Test Hall", "aoe2mc.tech.TESTING": "Learn Testing"}


def test_read_table_skips_comments_and_blank_lines():
    t = aoe2_lang.read_table(DATA / "en" / "strings" / "key-value" / "key-value-strings-utf8.txt")
    assert t == {"101": "Testunit", "102": "Test Hall", "103": "Learn Testing"}


def test_lang_files_give_each_key_by_its_english_string(monkeypatch):
    monkeypatch.setattr(aoe2_lang, "names", lambda: NAMES)
    files = aoe2_lang.lang_files(DATA, {"de": "de_de", "en": "en_us"})
    assert set(files) == {"de_de"}                                   # English: the fallback of the client
    assert files["de_de"] == {"aoe2mc.unit.TESTUNIT": "Prüfling", "aoe2mc.unit.TEST_HALL": "Prüfhalle"}


def test_names_have_the_keys_of_lang_name():
    import game.lang as lang
    n = aoe2_lang.names()
    assert n and all(k.startswith(("aoe2mc.unit.", "aoe2mc.tech.")) and v for k, v in n.items())
    unit = next(k for k in n if k.startswith("aoe2mc.unit."))
    assert lang.name(unit.split(".", 2)[2])["translate"] == unit


def test_add_to_pack_merges_into_the_lang_file_of_the_world(tmp_path, monkeypatch):
    monkeypatch.setattr(aoe2_lang, "names", lambda: NAMES)
    pack = tmp_path / "resourcepacks" / "resources.zip"
    pack.parent.mkdir()
    with zipfile.ZipFile(pack, "w") as z:
        z.writestr("pack.mcmeta", "{}")
        z.writestr("assets/aoe2mc/lang/de_de.json", json.dumps({"aoe2mc.other": "Andere"}))
    assert aoe2_lang.main([str(DATA), str(tmp_path)]) == 0
    with zipfile.ZipFile(pack) as z:
        de = json.loads(z.read("assets/aoe2mc/lang/de_de.json"))
        assert z.read("pack.mcmeta") == b"{}"
    assert de["aoe2mc.other"] == "Andere" and de["aoe2mc.unit.TESTUNIT"] == "Prüfling"


def test_a_world_with_no_pack_stops(tmp_path):
    with pytest.raises(SystemExit):
        aoe2_lang.main([str(DATA), str(tmp_path)])
