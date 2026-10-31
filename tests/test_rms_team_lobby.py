"""The lobby labels TEAM_GAME, TEAMS_CONNECTED and FIXED_POSITIONS of a random map script (#5050, decision #5052):
the lobby box "Team Together" defines FIXED_POSITIONS; the DE lobby never defines TEAM_GAME or TEAMS_CONNECTED."""
import numpy as np
import pytest

import aoe2mc
import rmap

BLOCKS = (("TEAM_GAME", "DESERT"), ("TEAMS_CONNECTED", "SNOW"), ("FIXED_POSITIONS", "BEACH"))


def script(label, terrain):
    return f"<LAND_GENERATION>\nbase_terrain GRASS\nif {label}\nbase_terrain {terrain}\nendif\n"


def land(text, **kw):
    return np.array(rmap.generate(text, 3, warn=lambda m: None, **kw)["terrain"])


@pytest.mark.parametrize("teams", [None, [1, 2], [1, 1]])
@pytest.mark.parametrize("together", [True, False])
@pytest.mark.parametrize("label,terrain", BLOCKS)
def test_each_block_gives_its_land_only_with_its_lobby_setting(label, terrain, together, teams):
    got = int(land(script(label, terrain), players=2, teams=teams, together=together)[0, 0])
    on = label == "FIXED_POSITIONS" and together
    assert got == rmap.TERRAINS[terrain if on else "GRASS"]


def test_team_together_is_on_by_default():
    label, terrain = BLOCKS[2]
    assert int(land(script(label, terrain))[0, 0]) == rmap.TERRAINS[terrain]


def test_the_same_seed_gives_the_same_map():
    text = "".join(script(label, terrain) for label, terrain in BLOCKS)
    assert (land(text, players=4, teams=[1, 1, 2, 2]) == land(text, players=4, teams=[1, 1, 2, 2])).all()


def test_the_survey_shows_fixed_positions_as_defined():
    assert "FIXED_POSITIONS" in rmap.lobby_labels()
    assert not {"TEAM_GAME", "TEAMS_CONNECTED"} & rmap.lobby_labels()


@pytest.mark.parametrize("args,together", [([], True), (["--no-team-together"], False)])
def test_the_option_sets_team_together(tmp_path, monkeypatch, args, together):
    got = {}
    monkeypatch.setattr(aoe2mc, "convert", lambda *a, **kw: got.update(kw))
    aoe2mc.main([str(tmp_path / "map.rms"), str(tmp_path / "out"), *args])
    assert got["together"] is together
