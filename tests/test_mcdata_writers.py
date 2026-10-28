"""Both writers of tools/mcdata/VERSION.json write the same keys, with the sound list (#2644, #2662)."""
import io
import json
import os
import sys
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import fetch_mcdata  # noqa: E402
import mc_check  # noqa: E402
import mcvalid  # noqa: E402


REGISTRIES = {
    "minecraft:entity_type": {"entries": {"minecraft:villager": {}, "minecraft:zombie": {}}},
    "minecraft:sound_event": {"entries": {"minecraft:entity.villager.yes": {}, "minecraft:block.stone.break": {}}},
}


def fake_jar(path):
    """A server jar with a bundle that holds one biome file, as mc_check.reports() reads it."""
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zz:
        zz.writestr("data/minecraft/worldgen/biome/plains.json", "{}")
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("META-INF/versions/26.3/server.jar", inner.getvalue())


def fake_run(cmd, cwd=None, **kwargs):
    """Stands in for the data generator: writes blocks.json and registries.json."""
    folder = os.path.join(cwd, "gen", "reports")
    os.makedirs(folder)
    with open(os.path.join(folder, "blocks.json"), "w") as f:
        json.dump({"minecraft:stone": {"properties": {}}}, f)
    with open(os.path.join(folder, "registries.json"), "w") as f:
        json.dump(REGISTRIES, f)


@pytest.fixture
def mcdata(tmp_path, monkeypatch):
    """Point both writers at tmp_path; return the folder of the data files."""
    out = tmp_path / "tools" / "mcdata"
    out.mkdir(parents=True)
    jar = tmp_path / "server.jar"
    fake_jar(jar)
    monkeypatch.setattr(mc_check, "ROOT", str(tmp_path))
    monkeypatch.setattr(mc_check, "server_jar", lambda version: str(jar))
    monkeypatch.setattr(mc_check, "java_for", lambda version: "java")
    monkeypatch.setattr(mc_check.subprocess, "run", fake_run)
    monkeypatch.setattr(fetch_mcdata, "OUT", str(out))
    mcmeta = {
        "blocks/data.json": {"minecraft:stone": [{}, None]},
        "registries/data.json": {"entity_type": ["minecraft:villager", "minecraft:zombie"],
                                 "worldgen/biome": ["plains"],
                                 "sound_event": ["entity.villager.yes", "block.stone.break"]},
    }
    monkeypatch.setattr(fetch_mcdata, "get", lambda version, path: mcmeta[path])
    monkeypatch.setattr(mcvalid, "DATA_DIR", str(out))
    mcvalid.data.cache_clear()          # data() is cached: a fake file must not stay for the next test
    yield out
    mcvalid.data.cache_clear()


def test_both_writers_write_the_same_keys(mcdata):
    mc_check.reports("26.3")
    reports_keys = set(json.loads((mcdata / "26.3.json").read_text()))
    fetch_mcdata.main("26.3")
    fetch_keys = set(json.loads((mcdata / "26.3.json").read_text()))
    assert reports_keys == fetch_keys
    assert "sounds" in reports_keys


def test_reports_sound_list_is_readable_by_mcvalid(mcdata):
    mc_check.reports("26.3")
    assert mcvalid.sound_error("minecraft:entity.villager.yes", "26.3") is None
    assert mcvalid.sound_error("minecraft:no.such.sound", "26.3") is not None
