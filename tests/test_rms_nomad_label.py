"""--nomad and --antiquity define the lobby labels NOMAD_MAP and ANTIQUITY_MODE of a random map script (#5017)."""
import pytest

import aoe2mc
import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS land_percent 40 }
<OBJECTS_GENERATION>
if NOMAD_MAP
create_object VILLAGER { set_place_for_every_player }
else
create_object TOWN_CENTER { set_place_for_every_player }
endif
"""


def names(labels=()):
    return [o["name"] for o in rmap.generate(SCRIPT, 1, size=100, warn=lambda m: None, labels=labels)["objects"]]


def test_the_nomad_label_gives_no_town_center():
    assert "TOWN_CENTER" in names()
    assert "TOWN_CENTER" not in names(("NOMAD_MAP",)) and names(("NOMAD_MAP",))


@pytest.mark.parametrize("flag", sorted(rmap.LOBBY_LABELS))
def test_each_flag_gives_its_label(tmp_path, monkeypatch, flag):
    got = {}
    (tmp_path / "a.rms").write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(aoe2mc, "convert", lambda src, out, **kw: got.update(kw))
    aoe2mc.main([str(tmp_path / "a.rms"), str(tmp_path / "W"), f"--{flag}"])
    assert got["labels"] == (rmap.LOBBY_LABELS[flag],)
