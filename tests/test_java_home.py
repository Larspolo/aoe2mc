"""The plugin build takes JAVA_HOME from the java.home of Java itself (#1126): on macOS /usr/bin/java is a stub."""
import os

from game import run


def fake_java(tmp_path, home):
    """A java that prints the properties to stderr as the real one does, and lives outside its home."""
    java = tmp_path / "stub" / "java"
    java.parent.mkdir()
    java.write_text(f"#!/bin/sh\necho '    java.class.path = ' >&2\necho '    java.home = {home}' >&2\n"
                    "echo 'openjdk version \"25\"' >&2\n")
    java.chmod(0o755)
    return str(java)


def test_java_home_reads_the_property(tmp_path):
    assert run.java_home(fake_java(tmp_path, "/opt/jdk 25/Home")) == "/opt/jdk 25/Home"


def test_build_plugin_gives_gradle_the_java_home(tmp_path, monkeypatch):
    home = tmp_path / "jdk"
    (home / "bin").mkdir(parents=True)
    (home / "bin" / "javac").touch()
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    gradlew = plugin / "gradlew"                 # writes the JAVA_HOME that it gets and a jar, no real build
    gradlew.write_text('#!/bin/sh\nmkdir -p build/libs\necho "$JAVA_HOME" > home.txt\n'
                       'touch build/libs/aoe2mc-plugin.jar\n')
    gradlew.chmod(0o755)
    monkeypatch.setattr(run, "PLUGIN", str(plugin))
    monkeypatch.setattr(run.mc_check, "java_for", lambda version: fake_java(tmp_path, home))
    jar = str(tmp_path / "out" / "aoe2mc-x.jar")
    run.build_plugin("26.3", jar)
    assert (plugin / "home.txt").read_text().strip() == str(home)
    assert os.path.exists(jar)
