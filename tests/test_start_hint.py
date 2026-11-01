"""The --play console text names the build controls of the game (#5492)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "game"))
import run  # noqa: E402


def test_start_hint_names_the_build_menu():
    assert "/trigger aoe_build" not in run.START_HINT
    assert "build menu" in run.START_HINT and "right click the ground" in run.START_HINT
