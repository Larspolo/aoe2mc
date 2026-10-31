"""DE base scenarios of old formats: fields that the format does not have, and values that the parser does not know (#5175)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import scenarios  # noqa: E402
from AoE2ScenarioParser.exceptions.asp_exceptions import UnsupportedAttributeError  # noqa: E402
from AoE2ScenarioParser.objects.managers.option_manager import OptionManager  # noqa: E402
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario  # noqa: E402

import aoe2mc  # noqa: E402


class Old(OptionManager):
    """An option manager of a format before 1.42."""
    @property
    def secondary_game_modes(self):
        raise UnsupportedAttributeError("The property 'secondary_game_modes' is supported since: 1.42.")


def test_no_secondary_game_modes(tmp_path, monkeypatch):
    """A format before 1.42 has no secondary_game_modes: the read gives no modes and no error."""
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    load = AoE2DEScenario.from_file

    def patched(path, *a, **k):
        scn = load(path, *a, **k)
        scn.option_manager.__class__ = Old
        return scn
    monkeypatch.setattr(AoE2DEScenario, "from_file", staticmethod(patched))
    assert "modes" not in aoe2mc.read_scenario(src)[4]["global_victory"]


def test_unknown_starting_age(tmp_path, monkeypatch):
    """A starting age that the parser does not know stays an int: the player gets no age."""
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    load = AoE2DEScenario.from_file

    def patched(path, *a, **k):
        scn = load(path, *a, **k)
        for p in scn.player_manager.players:
            p.__dict__["starting_age"] = 99
        return scn
    monkeypatch.setattr(AoE2DEScenario, "from_file", staticmethod(patched))
    players = aoe2mc.read_scenario(src)[6]
    assert all("age" not in p for p in players.values())
