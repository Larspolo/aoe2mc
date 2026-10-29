"""game/ and tools/ have no module of the same name: the full suite has both on sys.path, so one hides the other (#659)."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_no_module_name_in_game_and_tools():
    names = [{f for f in os.listdir(os.path.join(ROOT, d)) if f.endswith(".py")} for d in ("game", "tools")]
    assert not names[0] & names[1], f"rename one of each pair: {sorted(names[0] & names[1])}"
