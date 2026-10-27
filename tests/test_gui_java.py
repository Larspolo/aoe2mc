"""gui.java_problem (#1776): the window checks Java before it starts the game program. Fake `java -version` outputs
stand in for the installed Java."""
import subprocess

import gui

JDK25 = 'openjdk version "25.0.1" 2025-10-21\n    java.home = /jvm/25\n'
JDK21 = 'openjdk version "21.0.8" 2025-07-15\n    java.home = /jvm/21\n'


def fake(outputs):
    """A subprocess.run that gives the -version output of each java binary."""
    def run(cmd, **kw):
        if cmd[0] not in outputs:
            raise FileNotFoundError(cmd[0])
        return subprocess.CompletedProcess(cmd, 0, "", outputs[cmd[0]])
    return run


def problem(outputs, javac=(), **kw):
    return gui.java_problem("26.3", found=list(outputs), run=fake(outputs), exists=lambda p: p in javac, **kw)


def test_no_java():
    text = problem({}, system="Linux")
    assert text.startswith("No Java was found: Minecraft 26.3 needs Java 25.")
    assert "sudo apt-get install openjdk-25-jdk-headless" in text
    assert "brew install openjdk@25" in problem({}, system="Darwin")
    assert "https://adoptium.net/temurin/releases/?version=25" in problem({}, system="Windows")
    assert gui.java_problem(found=["/gone/java"], run=fake({})).startswith("No Java")   # a binary that does not run


def test_java_21_is_too_old():
    text = problem({"/jvm/21/bin/java": JDK21}, javac={"/jvm/21/bin/javac"}, system="Linux")
    assert text.startswith("Java 21 is too old: Minecraft 26.3 needs Java 25.")


def test_java_25_without_javac():
    text = problem({"/jvm/25/bin/java": JDK25}, system="Darwin")
    assert "Java 25 has no javac" in text and "brew install openjdk@25" in text and "vanilla" in text
    assert problem({"/jvm/25/bin/java": JDK25}, jdk=False) is None            # the vanilla server needs no plugin


def test_java_25_jdk():
    assert problem({"/jvm/25/bin/java": JDK25}, javac={"/jvm/25/bin/javac"}) is None
    assert problem({"/jvm/25/bin/java": JDK25}, javac={"/jvm/25/bin/javac.exe"}) is None   # Windows
    # The first java on the PATH is old, a later one (/usr/lib/jvm) is new: run.py finds that one too.
    assert problem({"/jvm/21/bin/java": JDK21, "/jvm/25/bin/java": JDK25}, javac={"/jvm/25/bin/javac"}) is None


def test_this_machine_gives_a_text_or_none():
    assert gui.java_problem() is None or "Java" in gui.java_problem()
