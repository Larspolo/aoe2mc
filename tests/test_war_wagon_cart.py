"""War Wagon (#2746): one horse pulls a cart, as in AoE2. The horse is the unit; an item_display of a chest rides it as
the cart (units.cart). With --resource-pack the chest with the custom_model_data "aoe2mc:war_wagon" is the cart model
of the pack (aoe2mc.cart_model). The horse shoots as a siege unit of the plugin, and the plugin turns the cart with it."""
import json
import shutil
import time
import zipfile

import numpy as np
import pytest
from test_ranged import data
from test_siege_walk import summon

import aoe2mc
import units
from game import ai, combat, run


def wagon(name="WAR_WAGON"):
    return units.make_entity({"name": name, "player": 1, "x": 0, "y": 0}, {}, (0.5, 64, 0.5), np.random.default_rng(0))


@pytest.mark.parametrize("name", ["WAR_WAGON", "ELITE_WAR_WAGON"])
def test_a_war_wagon_is_a_horse_with_a_cart_display(name):
    nbt = wagon(name)
    cart, = nbt["Passengers"]
    assert nbt["id"] == "minecraft:horse" and units.top_entity(nbt) is nbt          # the horse has the name and tags
    assert "aoe2mc.p1" in nbt["Tags"] and "aoe2mc.mount" in cart["Tags"]          # the cart is no unit of its own
    assert cart["id"] == "minecraft:item_display" and cart["item"]["id"] == "minecraft:chest"   # vanilla: a chest
    assert list(cart["item"]["components"]["minecraft:custom_model_data"]["strings"]) == ["aoe2mc:war_wagon"]
    assert cart["transformation"]["translation"][2] < -1                           # behind the horse
    assert not units.siege(name) and units.wagon(name) and not units.wagon("KNIGHT")


def test_the_horse_shoots_with_the_values_of_the_war_wagon():
    s = combat.stats("WAR_WAGON")                                     # range in blocks, reload in ticks, siege: blast
    assert combat.range_command("u", "WAR_WAGON", 4).split()[3:] == [
        str(s.range * 4), str(max(1, round(s.reload / ai.NORMAL * 20))), str(combat.BLAST.get("WAR_WAGON", 0) * 4)]
    assert combat.range_command("u", "ELITE_WAR_WAGON", 4).split()[3] == str(combat.stats("ELITE_WAR_WAGON").range * 4)
    assert ai.speed_command("u", "WAR_WAGON", 4).startswith("attribute u minecraft:movement_speed")   # no carrier


def test_the_pack_has_the_cart_model_and_keeps_the_vanilla_chest(tmp_path):
    names = aoe2mc.write_resourcepack(str(tmp_path))
    with zipfile.ZipFile(tmp_path / "resourcepacks" / "resources.zip") as z:
        chest = json.loads(z.read("assets/minecraft/items/chest.json"))["model"]
        model = json.loads(z.read("assets/aoe2mc/models/item/war_wagon.json"))
    assert "assets/aoe2mc/models/item/war_wagon.json" in names
    assert chest["property"] == "minecraft:custom_model_data" and chest["fallback"] == aoe2mc.VANILLA_CHEST
    assert chest["cases"] == [{"when": "aoe2mc:war_wagon",
                               "model": {"type": "minecraft:model", "model": "aoe2mc:item/war_wagon"}}]
    xyz = [v for e in model["elements"] for v in e["from"] + e["to"]]
    assert -16 <= min(xyz) and max(xyz) <= 32                                      # the limit of a block model
    assert all(0 <= v <= 16 for e in model["elements"] for f in e["faces"].values() for v in f["uv"])
    assert set(model["textures"].values()) <= {f"minecraft:block/{t}" for b in aoe2mc.CART_BOXES for t in b[2:]} | \
        {"minecraft:block/dark_oak_log"}


@pytest.mark.mc
def test_a_war_wagon_walks_shoots_and_keeps_its_cart_behind(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 30}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 26} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert "Summoned" in summon(game, "WAR_WAGON", x0 + 2.5, y, z0 + 2.5, "ww")
        ww = "@e[type=horse,tag=ww,limit=1]"
        game.command(f"team join p1 {ww}")
        assert game.command(combat.stats_command(ww, "WAR_WAGON")).strip() == "Stats: 1 units"
        assert game.command(combat.range_command(ww, "WAR_WAGON", 4)).strip() == "Range: 1 units"
        assert ai.move(game, ww, "WAR_WAGON", 4, x0 + 14.5, y, z0 + 2.5).strip() == "Moved 1 units"   # east
        end = time.time() + 20
        while time.time() < end and data(game, "ww", "Pos")[0] < x0 + 12:
            time.sleep(0.5)
        time.sleep(1)

        def yaws():
            horse = data(game, "ww", "Rotation")[0]
            cart = game.command(f"execute as {ww} on passengers run data get entity @s Rotation")
            return horse, float(cart.split("[")[1].split("f")[0])

        def apart(a, b):
            return abs((a - b + 180) % 360 - 180)
        horse, cart = yaws()
        assert apart(horse, -90) < 30 and apart(horse, cart) < 15, (horse, cart)     # it faces east, the cart too
        game.command(f'summon zombie {x0 + 13.5} {y} {z0 + 24.5} {{NoAI:1b,IsBaby:0b,Tags:["m1"]}}')   # 22 blocks south
        game.command("team join p2 @e[tag=m1]")
        game.command("aoe stats @e[tag=m1,limit=1] 1000 4 0 1 0 infantry -")       # militia values
        assert game.command(f"aoe attack {ww} @e[tag=m1,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 30
        while time.time() < end and (data(game, "m1", "Health") or [1000.0])[0] == 1000.0:
            time.sleep(0.2)
        assert (data(game, "m1", "Health") or [1000.0])[0] < 1000.0               # it walked into range and shot
        time.sleep(1)
        horse, cart = yaws()
        assert apart(horse, 0) < 45 and apart(horse, cart) < 15, (horse, cart)       # it turned south, the cart too
