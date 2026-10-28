"""gui.needs_jdk (#3050): only a checkout builds the Paper plugin, so only it needs javac. An app bundle (sys.frozen)
brings the plugin jar and needs a Java runtime, not a JDK."""
import sys

import gui
from test_gui_java import JDK25, problem


def test_bundle_accepts_java_25_without_javac(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert gui.needs_jdk("paper") is False
    assert problem({"/jvm/25/bin/java": JDK25}, system="Linux", jdk=gui.needs_jdk("paper")) is None


def test_checkout_paper_still_needs_javac(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert gui.needs_jdk("paper") is True
    text = problem({"/jvm/25/bin/java": JDK25}, system="Linux", jdk=gui.needs_jdk("paper"))
    assert "Java 25 has no javac" in text


def test_vanilla_needs_no_javac(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert gui.needs_jdk("vanilla") is False
    assert problem({"/jvm/25/bin/java": JDK25}, system="Linux", jdk=gui.needs_jdk("vanilla")) is None
