"""#2741: the game program of a release bundle sends the link of the resource pack of the GitHub release, when the world
pack is the release pack; else the local server of #2740."""
import hashlib
import importlib.util
import json
import os
import sys

from game import run

# packaging/ is no package (the name of a PyPI package): load the script by its path
SPEC = importlib.util.spec_from_file_location("release_pack", os.path.join(os.path.dirname(__file__), "..", "packaging",
                                                                           "release_pack.py"))
release_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_pack)

DATA = b"PK the pack of the release"


def world(tmp_path, data=DATA):
    (tmp_path / "w" / "resourcepacks").mkdir(parents=True)
    (tmp_path / "w" / "resourcepacks" / "resources.zip").write_bytes(data)
    return run.pack_file(str(tmp_path / "w"))


def bundle(tmp_path, monkeypatch, sha1=hashlib.sha1(DATA).hexdigest()):
    """A frozen bundle with release.json of the tag v1.2.0."""
    (tmp_path / "release.json").write_text(json.dumps({"tag": "v1.2.0", "sha1": sha1}))
    monkeypatch.setattr(run, "RELEASE", str(tmp_path / "release.json"))
    monkeypatch.setattr(sys, "frozen", True, raising=False)


def test_a_bundle_with_the_release_pack_gives_the_release_link(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch)
    pack = run.pack_source(world(tmp_path))
    assert pack.url == "https://github.com/Larspolo/aoe2mc/releases/download/v1.2.0/aoe2mc-resourcepack.zip"
    assert f"resource-pack-sha1={hashlib.sha1(DATA).hexdigest()}" in run.properties(1, 2, "pw", pack).splitlines()
    pack.stop()


def test_a_world_pack_of_another_version_gives_the_local_link(tmp_path, monkeypatch):
    bundle(tmp_path, monkeypatch, sha1="0" * 40)
    pack = run.pack_source(world(tmp_path))
    try:
        assert pack.url.startswith("http://127.0.0.1:") and pack.sha1 == hashlib.sha1(DATA).hexdigest()
    finally:
        pack.stop()


def test_from_the_source_it_gives_the_local_link(tmp_path, monkeypatch):
    (tmp_path / "release.json").write_text(json.dumps({"tag": "v1.2.0", "sha1": hashlib.sha1(DATA).hexdigest()}))
    monkeypatch.setattr(run, "RELEASE", str(tmp_path / "release.json"))
    monkeypatch.delattr(sys, "frozen", raising=False)
    pack = run.pack_source(world(tmp_path))
    try:
        assert pack.url.startswith("http://127.0.0.1:")
    finally:
        pack.stop()


def test_the_release_pack_has_the_bytes_of_the_world_pack(tmp_path):
    import aoe2mc
    aoe2mc.write_resourcepack(str(tmp_path / "w"))
    release_pack.main(str(tmp_path / "dist" / "aoe2mc-resourcepack.zip"))
    assert (tmp_path / "dist" / "aoe2mc-resourcepack.zip").read_bytes() == \
        (tmp_path / "w" / "resourcepacks" / "resources.zip").read_bytes()
    assert os.path.getsize(tmp_path / "dist" / "aoe2mc-resourcepack.zip") > 1000


def test_a_stored_png_has_the_pixels_of_the_image():
    import io

    from PIL import Image

    import aoe2mc
    im = Image.new("RGBA", (300, 300), (10, 20, 30, 40))              # more than one stored block of 65535 bytes
    im.putpixel((299, 299), (1, 2, 3, 255))
    data = aoe2mc.stored_png(im)
    assert Image.open(io.BytesIO(data)).tobytes() == im.tobytes()
    assert data == aoe2mc.stored_png(im.copy())


def test_windows_writes_the_same_zip(tmp_path, monkeypatch):
    import aoe2mc
    aoe2mc.write_resourcepack(str(tmp_path / "a"))
    monkeypatch.setattr(sys, "platform", "win32")                      # zipfile.ZipInfo reads it
    aoe2mc.write_resourcepack(str(tmp_path / "b"))
    assert (tmp_path / "a" / "resourcepacks" / "resources.zip").read_bytes() == \
        (tmp_path / "b" / "resourcepacks" / "resources.zip").read_bytes()
