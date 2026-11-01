import sys

from game import run


def test_python_names_run_py(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert run.program() == "python3 game/run.py"


def test_installer_names_its_program(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["/Applications/aoe2mc.app/Contents/MacOS/aoe2mc-game", "W"])
    assert run.program() == "aoe2mc-game"
