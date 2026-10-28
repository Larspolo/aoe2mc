"""#2743: with --resource-pack each unit with armor wears its own equipment asset aoe2mc:<name>: the archers, the
riders of the cavalry and the horse armor of the mounted units (layer horse_body), the heroes too."""
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


@pytest.fixture
def assets(monkeypatch):
    monkeypatch.setattr(units, "ASSETS", True)


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    out = tmp_path_factory.mktemp("pack")
    aoe2mc.write_resourcepack(str(out))
    with zipfile.ZipFile(out / "resourcepacks" / "resources.zip") as z:
        yield z


def asset(piece):
    e = piece.get("components", {}).get("minecraft:equippable")
    return e and (str(e["slot"]), str(e["asset_id"]))


def all_units():
    """Each AoE2 unit and hero name of AoE2ScenarioParser and data/units.jsonl, with its hero flag."""
    names = {e.name: False for e in UnitInfo} | {r["name"]: r["name"] in units.HERO_BASE for r in units.UNITS}
    return names | {e.name: True for e in HeroInfo}


def test_each_armor_piece_of_each_unit_has_the_asset_of_its_unit(assets):
    armored = 0
    for name, hero in all_units().items():
        worn = units.pieces(units.classify(name, hero) or {})
        armored += bool(worn)
        for slot, piece in worn.items():
            assert asset(piece) == (slot, "aoe2mc:" + units.asset(name).lower()), name
    assert armored > 400


def test_archers_riders_and_horses_wear_their_own_asset(assets):
    for name in ("ARCHER", "ARBALESTER", "CAVALRY_ARCHER", "KNIGHT", "PALADIN", "CATAPHRACT", "CAMEL_RIDER"):
        assert {asset(p)[1] for p in units.pieces(units.classify(name)).values()} == {"aoe2mc:" + name.lower()}, name
    knight = units.classify("KNIGHT")
    assert asset(knight["equipment"]["body"]) == ("body", "aoe2mc:knight")             # the horse armor
    assert asset(units.classify("ELITE_CATAPHRACT")["equipment"]["body"]) == ("body", "aoe2mc:cataphract")  # ELITE_X: X


def test_a_hero_has_its_own_asset_and_the_look_of_its_base(assets):
    hero = next(h for h, b in units.HERO_BASE.items() if b == "PALADIN")
    assert {asset(p)[1] for p in units.pieces(units.classify(hero, True)).values()} == {"aoe2mc:" + hero.lower()}
    assert units.look(hero, True) == units.LOOKS["PALADIN"]


def test_without_the_option_the_items_are_as_today():
    assert not units.ASSETS
    for name, hero in all_units().items():
        assert not any(asset(p) for p in units.pieces(units.classify(name, hero) or {}).values()), name


def test_the_pack_has_the_equipment_of_each_asset(pack):
    files = set(pack.namelist())
    for name, hero in units.dressed().items():
        worn = units.pieces(units.describe(name, hero))
        layers = json.loads(pack.read(f"assets/aoe2mc/equipment/{units.asset(name).lower()}.json"))["layers"]
        assert ("horse_body" in layers) == ("body" in worn), name
        for layer, (base, over) in layers.items():
            for tex in (base["texture"], over["texture"]):
                assert f"assets/aoe2mc/textures/entity/equipment/{layer}/{tex.split(':')[1]}.png" in files, name


def test_units_with_no_look_line_share_textures(pack):
    tex = [n for n in pack.namelist() if n.startswith("assets/aoe2mc/textures/entity/equipment/humanoid/")]
    assert len(tex) < 2 * len(units.dressed())
    assert any("/look_" in n for n in tex)


def texture(pack, layer, name):
    layers = json.loads(pack.read(f"assets/aoe2mc/equipment/{name}.json"))["layers"]
    path = f"assets/aoe2mc/textures/entity/equipment/{layer}/{layers[layer][0]['texture'].split(':')[1]}.png"
    return np.array(Image.open(io.BytesIO(pack.read(path))).convert("RGBA"))


def test_the_horse_armor_covers_the_body_but_not_the_legs(pack):
    knight, cataphract = texture(pack, "horse_body", "knight"), texture(pack, "horse_body", "cataphract")
    assert knight.shape == (64, 64, 4)
    assert knight[58, 10, 3] == 255 and knight[16, 9, 3] == 255           # a side of the body, the top of the head
    assert knight[5, 50, 3] == 0                                          # no armor on the legs
    assert cataphract[58, 10, 0] > cataphract[58, 10, 2] + 60             # golden horse armor


def test_a_mounted_unit_of_the_lines_has_the_armor_of_its_rider(pack):
    assert texture(pack, "humanoid", "centurion")[..., 3].any()


def test_the_summon_command_of_each_unit_with_its_assets_fits_into_rcon(assets):
    from game import rcon
    for name, hero in all_units().items():
        nbt = units.make_entity({"name": name, "player": 1, "hero": hero}, {1: {"color": "BLUE"}}, (1234.5, 63.0, 1234.5),
                                np.random.default_rng(1))
        if nbt is not None:
            kind, _ = nbt.pop("id"), nbt.pop("Pos")
            assert len(f"summon {kind} 1234.5 63.0 1234.5 {units.summon_snbt(nbt)}".encode()) <= rcon.MAX, name


@pytest.mark.mc
def test_a_paladin_that_a_game_on_a_pack_world_summons_keeps_its_assets(tiny_world, tmp_path):
    import shutil

    from test_mounted_attack import floor
    from test_paper import paper_reachable

    from game import gather, run, train
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    aoe2mc.write_resourcepack(str(world))
    x0, y, z0 = 1, 200, 1
    with run.Game(world) as game:                                    # the pack turns units.ASSETS on (conftest: off after)
        floor(game, x0, y, z0, 10)
        g = gather.Gather(game, json.loads((world / "aoe2mc.json").read_text())).setup()
        uuid = train.summon(g, "PALADIN", (x0 + 0.5, y, z0 + 2.5))
        body = game.command(f"data get entity {uuid} equipment.body.components")
        head = game.command(f"execute as {uuid} on passengers run data get entity @s equipment.head.components")
    assert '"aoe2mc:paladin"' in body and '"aoe2mc:paladin"' in head, (body, head)
