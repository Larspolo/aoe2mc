"""--resources and --age define the lobby labels of the starting resources and the starting age of a random map
script (#5016)."""
import pytest

import aoe2mc
import rmap

SCRIPT = """<PLAYER_SETUP>
random_placement
<LAND_GENERATION>
base_terrain GRASS
create_player_lands { terrain_type GRASS land_percent 40 }
<OBJECTS_GENERATION>
if INFINITE_RESOURCES
create_object GOLD { set_place_for_every_player }
endif
if DARK_AGE_START
create_object TOWN_CENTER { set_place_for_every_player }
endif
"""


def names(labels):
    return {o["name"] for o in rmap.generate(SCRIPT, 1, size=100, warn=lambda m: None, labels=labels)["objects"]}


def labels(tmp_path, monkeypatch, *flags):
    got = {}
    (tmp_path / "a.rms").write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(aoe2mc, "convert", lambda src, out, **kw: got.update(kw))
    aoe2mc.main([str(tmp_path / "a.rms"), str(tmp_path / "W"), *flags])
    return got["labels"]


def test_the_blocks_give_the_objects_of_the_setting(tmp_path, monkeypatch):
    infinite = labels(tmp_path, monkeypatch, "--resources", "infinite")
    assert names(infinite) == {"GOLD_MINE", "TOWN_CENTER"} or {"TOWN_CENTER"} < names(infinite)
    assert "TOWN_CENTER" not in names(labels(tmp_path, monkeypatch, "--age", "feudal"))
    assert not any("GOLD" in n for n in names(labels(tmp_path, monkeypatch)))


@pytest.mark.parametrize("value", sorted(rmap.RESOURCE_LABELS))
def test_each_resource_value_gives_its_label(tmp_path, monkeypatch, value):
    got = labels(tmp_path, monkeypatch, "--resources", value)
    assert {*got} - set(rmap.AGE_LABELS.values()) == ({rmap.RESOURCE_LABELS[value]} - {None})


@pytest.mark.parametrize("age", sorted(rmap.AGE_LABELS))
def test_each_age_gives_its_label(tmp_path, monkeypatch, age):
    assert rmap.AGE_LABELS[age] in labels(tmp_path, monkeypatch, "--age", age)
