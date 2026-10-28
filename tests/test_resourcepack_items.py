"""#2744: with --resource-pack the hand items of the units get AoE2 weapon models (minecraft:item_model aoe2mc:<weapon>)
that the pack has: an items file, a model and its texture. The item id stays, as the mob fights with it."""
import io
import json
import zipfile

import numpy as np
import pytest
from AoE2ScenarioParser.datasets.heroes import HeroInfo
from AoE2ScenarioParser.datasets.units import UnitInfo
from PIL import Image

import aoe2mc
import units

NAMES = sorted({u.name for u in UnitInfo} | {h.name for h in HeroInfo} | set(units.LINES))
NOT_WEAPONS = {"minecraft:torch", "minecraft:saddle"}                  # the joke torch; no hand items besides


def hand_items(nbt):
    stack, out = [nbt], []
    while stack:
        e = stack.pop()
        stack += list(e.get("Passengers", []))
        out += [it for slot, it in e.get("equipment", {}).items() if slot in ("mainhand", "offhand") and "id" in it]
    return out


def entity(name, models=True):
    old, units.ASSETS = units.ASSETS, models
    try:
        return units.make_entity({"name": name, "player": 1, "x": 0, "y": 0}, {1: {"color": "blue"}}, (0.5, 70, 0.5),
                                 np.random.default_rng(0))
    finally:
        units.ASSETS = old


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("pack")
    aoe2mc.write_resourcepack(str(out))
    with zipfile.ZipFile(out / "resourcepacks" / "resources.zip") as z:
        return {n: z.read(n) for n in z.namelist()}


def test_each_hand_item_of_each_unit_has_a_model_of_the_pack(pack):
    seen = set()
    for name in NAMES:
        for it in hand_items(entity(name) or {}):
            if str(it["id"]) in NOT_WEAPONS:
                continue
            model = str(it["components"]["minecraft:item_model"])
            assert model.startswith("aoe2mc:"), (name, it)
            seen.add(model[7:])
    assert {"halberd", "spear", "longbow", "throwing_axe", "bow", "crossbow", "sword", "shield"} <= seen
    for w in seen:
        items = json.loads(pack[f"assets/aoe2mc/items/{w}.json"])
        assert items["model"] == {"type": "minecraft:model", "model": f"aoe2mc:item/{w}"}
        model = json.loads(pack[f"assets/aoe2mc/models/item/{w}.json"])
        assert model["textures"]["layer0"] == f"aoe2mc:item/{w}"
        im = Image.open(io.BytesIO(pack[f"assets/aoe2mc/textures/item/{w}.png"]))
        assert im.size == (16, 16) and im.convert("RGBA").getextrema()[3][1] == 255   # not empty


@pytest.mark.parametrize("name, item, model", [("HALBERDIER", "trident", "halberd"), ("SPEARMAN", "trident", "spear"),
                                               ("LONGBOWMAN", "bow", "longbow"), ("ARCHER", "bow", "bow"),
                                               ("THROWING_AXEMAN", None, "throwing_axe"),
                                               ("MAN_AT_ARMS", "stone_sword", "sword")])
def test_the_aoe2_weapon_of_a_unit(name, item, model):
    main = entity(name)["equipment"]["mainhand"]
    assert item is None or str(main["id"]) == "minecraft:" + item          # the mob still fights with its item
    assert str(main["components"]["minecraft:item_model"]) == "aoe2mc:" + model


def test_the_shield_in_the_off_hand():
    off = entity("MAN_AT_ARMS")["equipment"]["offhand"]
    assert str(off["components"]["minecraft:item_model"]) == "aoe2mc:shield"


def test_without_the_option_the_items_are_as_today():
    for name in ("HALBERDIER", "LONGBOWMAN", "MAN_AT_ARMS", "KNIGHT"):
        assert all("minecraft:item_model" not in it.get("components", {}) for it in hand_items(entity(name, False)))


def test_the_game_program_uses_the_models_of_a_world_with_the_pack(tmp_path):
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
    import run
    old = units.ASSETS
    try:
        run.Game(str(tmp_path))
        assert units.ASSETS is False
        (tmp_path / "resourcepacks").mkdir()
        (tmp_path / "resourcepacks" / "resources.zip").write_bytes(b"")
        run.Game(str(tmp_path))
        assert units.ASSETS is True
    finally:
        units.ASSETS = old
