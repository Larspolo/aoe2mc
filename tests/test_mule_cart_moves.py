"""game/build.py: the mule cart moves (#2209, AoE2 DE wiki "Mule Cart", MediaWiki API, 2026-10-27: a building that
moves, speed 0.8). A complete mule cart is a mule with a chest, the mob path finding walks it to a clicked place, and
its drop cells follow it. Fake server, no Minecraft."""
import json
import shutil
import time

import pytest
from test_mule_cart import done

import units
from game import ai, build, gather, train


def cart(g):
    site, = g.sites
    return site, site["uuid"]


def test_a_complete_mule_cart_is_a_mule_with_a_chest():
    server, g, cells = done()
    site, u = cart(g)
    summon = next(c for c in server.log if c.startswith("summon minecraft:mule "))
    assert "ChestedHorse:1b" in summon and g.soldiers[u] == "MULE_CART" and u not in g.villagers
    assert units.classify("MULE_CART")["id"] == "minecraft:mule"
    x0, x1, z0, z1 = site["footprint"]
    assert f"fill {x0} 64 {z0} {x1 - 1} " in "\n".join(server.log)     # the blocks of the cart design go
    assert not cells & g.map.blocked                                   # it blocks no path


def test_it_walks_to_a_clicked_place_and_takes_the_wood_there():
    server, g, cells = done([{"kind": "other", "name": "TREE_OAK", "tile": [5.5, 1.5]}])
    site, u = cart(g)
    g.selected = {u}
    server.entities["Steve"]["Pos"] = (30.5, 64.0, 16.5)              # it looks down at the block (30, 16)
    g.click("Steve")
    assert any(c.startswith(f"aoe moveto {u} 30.5 ") for c in server.log)
    g.selected = {"v0"}
    g.send((5, 1))
    v = g.villagers["v0"]
    drops = []
    for _ in range(400):
        g.step()
        if v.state == "to_drop" and not v.path:
            drops.append(v.cell)
    new = g.map.around(site["cells"])
    assert drops and all(c in new for c in drops) and not any(c in g.map.around(cells) for c in drops)
    assert server.wood() >= 10 and site["footprint"][0] <= 30 < site["footprint"][1]


def test_a_dead_mule_cart_takes_no_wood():
    server, g, cells = done()
    site, u = cart(g)
    del server.entities[u]
    build.moved_carts(g)
    assert all(not sites for r, sites in g.map.drops.items() if r in ("wood", "gold", "stone", "meat"))


def test_it_counts_for_no_population():
    server, g, cells = done()
    train.census(g)
    assert g.pop == 1 and gather.military("MULE_CART") is False       # only the villager


@pytest.mark.mc
def test_the_mule_walks_with_the_plugin_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                                            # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 12}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 10} stone_bricks")
        g = gather.Gather(game, json.loads((world / "aoe2mc.json").read_text())).setup()
        u = train.summon(g, "MULE_CART", (x0 + 2.5, float(y), z0 + 4.5))
        assert g.soldiers[u] == "MULE_CART"
        assert game.command("execute if entity @e[type=mule,nbt={ChestedHorse:1b}]").strip().endswith("1")
        cells = {(x0 + 2, z0 + 4)}
        site = {"name": "MULE_CART", "player": 1, "footprint": (x0 + 2, x0 + 3, z0 + 4, z0 + 5), "uuid": u, "cells": cells}
        g.sites.append(site)
        out = ai.move(g, u, "MULE_CART", g.map.T, x0 + 20.5, y, z0 + 4.5)
        assert out.strip() == "Moved 1 units", out
        end = time.time() + 30
        while time.time() < end and g.pos(u)[0] < x0 + 19:
            time.sleep(0.5)
        build.moved_carts(g)
        assert site["footprint"][0] >= x0 + 19 and site["cells"] is cells and min(cells)[0] >= x0 + 19
