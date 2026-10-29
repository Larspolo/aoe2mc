"""The Temurin JRE download of mc_check on each system (#3054)."""
import io
import json
import os
import sys
import tarfile
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import mc_check  # noqa: E402

import gui  # noqa: E402

NAMES = {"linux-x64": "OpenJDK25U-jre_x64_linux_hotspot_25.0.1_8.tar.gz",
         "linux-aarch64": "OpenJDK25U-jre_aarch64_linux_hotspot_25.0.1_8.tar.gz",
         "mac-aarch64": "OpenJDK25U-jre_aarch64_mac_hotspot_25.0.1_8.tar.gz",
         "mac-x64": "OpenJDK25U-jre_x64_mac_hotspot_25.0.1_8.tar.gz",
         "windows-x64": "OpenJDK25U-jre_x64_windows_hotspot_25.0.1_8.zip"}
LAYOUT = {"linux": "jdk-25.0.1+8-jre/bin/java", "mac": "jdk-25.0.1+8-jre/Contents/Home/bin/java",
          "windows": "jdk-25.0.1+8-jre/bin/java.exe"}


def archive(name):
    path, buf = LAYOUT[name.split("_")[2]], io.BytesIO()
    if name.endswith(".zip"):
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr(path, b"java")
    else:
        with tarfile.open(fileobj=buf, mode="w:gz") as t:
            info = tarfile.TarInfo(path)
            info.size, info.mode = 4, 0o755
            t.addfile(info, io.BytesIO(b"java"))
    return buf.getvalue()


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setattr(mc_check, "CACHE", str(tmp_path))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path.parent))
    urls = []

    def get(url):
        urls.append(url)
        if url.endswith("/latest"):
            return json.dumps({"assets": [{"name": n, "browser_download_url": "dl/" + n} for n in NAMES.values()]
                              + [{"name": "OpenJDK25U-jdk_x64_linux_hotspot_25.0.1_8.tar.gz",
                                  "browser_download_url": "dl/jdk"}]}).encode()
        return archive(url[3:])
    monkeypatch.setattr(mc_check, "get", get)
    return urls


@pytest.mark.parametrize("system, machine, key", [
    ("Linux", "x86_64", "linux-x64"), ("Linux", "aarch64", "linux-aarch64"), ("Darwin", "arm64", "mac-aarch64"),
    ("Darwin", "x86_64", "mac-x64"), ("Windows", "AMD64", "windows-x64")])
def test_download_takes_the_asset_and_layout_of_the_system(fake, tmp_path, system, machine, key):
    java = mc_check.download_jre(25, system, machine)
    assert fake[-1] == "dl/" + NAMES[key]
    assert java == str(tmp_path / "jdk-25" / LAYOUT[key.split("-")[0]])
    assert mc_check.cached_javas() == [java]       # find_java looks there: a second start does not download again


def test_gui_finds_each_layout(monkeypatch, tmp_path):
    cache = tmp_path / "aoe2mc" / "mc"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(gui.shutil, "which", lambda name: None)
    for i, path in enumerate(LAYOUT.values()):
        (cache / f"jdk-{i}" / path).parent.mkdir(parents=True)
        (cache / f"jdk-{i}" / path).write_text("java")
    found = [j for j in gui.javas() if j.startswith(str(cache))]       # not the Java of /usr/lib/jvm
    assert sorted(found) == sorted(str(cache / f"jdk-{i}" / p) for i, p in enumerate(LAYOUT.values()))
    monkeypatch.setattr(mc_check, "CACHE", str(cache))
    assert sorted(mc_check.cached_javas()) == sorted(found)


def test_java_for_without_geteuid_and_without_asset(fake, monkeypatch):
    monkeypatch.delattr(mc_check.os, "geteuid", raising=False)
    monkeypatch.setattr(mc_check, "version_json", lambda v: {"javaVersion": {"majorVersion": 25}})
    monkeypatch.setattr(mc_check, "find_java", lambda need: None)
    monkeypatch.setattr(mc_check.platform, "system", lambda: "Windows")
    monkeypatch.setattr(mc_check.platform, "machine", lambda: "AMD64")
    assert mc_check.java_for("26.3").endswith("java.exe")
    monkeypatch.setattr(mc_check.platform, "system", lambda: "SunOS")
    with pytest.raises(SystemExit, match="Minecraft 26.3 needs Java 25"):
        mc_check.java_for("26.3")
