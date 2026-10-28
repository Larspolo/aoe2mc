"""#2742: with --resource-pack each infantry unit of data/lines.jsonl (and the Spearman line) wears its own armor:
the equipment asset aoe2mc:<name> on each armor piece, and the pack has its equipment file and textures."""
import io
import json
import os
import zipfile

import numpy as np
import pytest
from PIL import Image

import aoe2mc
import units

PIECES = ("head", "chest", "legs", "feet")


@pytest.fixture
def assets(monkeypatch):
    monkeypatch.setattr(units, "ASSETS", True)


def worn(desc):
    while "equipment" not in desc:                       # a mounted unit: the rider
        desc = desc["Passengers"][0]
    return {s: p for s, p in desc["equipment"].items() if s in PIECES}


def asset(piece):
    e = piece.get("components", {}).get("minecraft:equippable")
    return e and (str(e["slot"]), str(e["asset_id"]))


def test_each_line_unit_has_a_look():
    assert set(units.LINES) <= set(units.LOOKS)


def test_each_armor_piece_has_the_asset_of_its_unit(assets):
    for name in units.LINES:
        for slot, piece in worn(units.line_unit(name)).items():
            assert asset(piece) == (slot, "aoe2mc:" + name.lower()), name


def test_the_militia_and_spearman_lines_differ(assets):
    ids = {n: {asset(p)[1] for p in worn(units.classify(n)).values()} for n in
           ("MILITIA", "MAN_AT_ARMS", "CHAMPION", "SPEARMAN", "PIKEMAN", "HALBERDIER")}
    assert all(v == {"aoe2mc:" + n.lower()} for n, v in ids.items())
    assert units.classify("ELITE_SERJEANT") != units.classify("SERJEANT")
    assert {asset(p)[1] for p in worn(units.classify("ELITE_SAMURAI")).values()} == {"aoe2mc:samurai"}   # elite: X's armor


def test_without_the_option_the_items_are_as_today():
    assert not units.ASSETS
    for name in units.LINES:
        assert not any(asset(p) for p in worn(units.line_unit(name)).values()), name


def test_the_pack_has_an_equipment_file_and_textures_for_each_unit(tmp_path):
    aoe2mc.write_resourcepack(str(tmp_path))
    with zipfile.ZipFile(tmp_path / "resourcepacks" / "resources.zip") as z:
        files = set(z.namelist())
        for name in set(units.LOOKS) & set(units.dressed()):           # a unit with no armor needs no asset (#2743)
            n = name.lower()
            layers = json.loads(z.read(f"assets/aoe2mc/equipment/{n}.json"))["layers"]
            assert {"humanoid", "humanoid_leggings"} <= set(layers)            # and "horse_body" for a mount (#2743)
            assert layers["humanoid"][0] == {"texture": f"aoe2mc:{n}", "dyeable": {"color_when_undyed": 0xFFFFFF}}
            for layer in layers:
                for end in ("", "_overlay"):
                    assert f"assets/aoe2mc/textures/entity/equipment/{layer}/{n}{end}.png" in files
        im = Image.open(io.BytesIO(z.read("assets/aoe2mc/textures/entity/equipment/humanoid/champion.png")))
        assert im.size == (64, 32)
        assert im.convert("RGBA").getpixel((20, 24))[2] > 150          # the diamond chestplate is cyan
        militia = np.array(Image.open(io.BytesIO(z.read("assets/aoe2mc/textures/entity/equipment/humanoid/militia.png"))))
        assert not (militia == np.array(im)).all()


def test_a_unit_that_the_game_program_trains_has_the_same_asset(tmp_path):
    from game import run
    os.makedirs(tmp_path / "resourcepacks")
    (tmp_path / "resourcepacks" / "resources.zip").write_bytes(b"")
    try:
        run.Game(str(tmp_path))
        nbt = units.make_entity({"name": "CHAMPION", "player": 1}, {}, (0, 64, 0), np.random.default_rng(1))
        assert {asset(p) for p in worn(nbt).values()} == {(s, "aoe2mc:champion") for s in PIECES}
    finally:
        units.ASSETS = False
    run.Game(str(tmp_path / "resourcepacks"))                         # a world without the pack
    assert not units.ASSETS
