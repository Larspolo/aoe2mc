"""game/savegame.py: a load puts the portcullis of each complete gate again (iron bars, and on Paper the plugin gate),
because the plugin forgets its gates at a load (#2762, #2988). A gate that fell before the save gets none."""
import json
import math

from test_build_gates import line
from test_build_site import site_map

from game import build, combat, savegame


def saved_gate(paper=True):
    """A complete palisade gate on Paper, saved: (the save dict, the Gather of the gate, its site)."""
    server, g = site_map(wood=200)
    g.paper = paper
    line(g, (6, 10), (11, 10))
    site = build.gate(g, "Steve", "PALISADE_GATE", (8, 10))
    build.rise(g, site, math.inf)
    return json.loads(json.dumps(savegame.dump(g))), g, site


def loaded(d, paper=True):
    server, h = site_map(wood=200)
    h.paper = paper
    savegame.load(h, d)
    return server


def test_a_load_sends_the_plugin_gate_of_a_complete_gate_again_on_paper():
    d, _, _ = saved_gate()
    server = loaded(d)
    assert "aoe gate p1 7 64 10 8 66 10" in server.log


def test_a_load_puts_the_iron_bars_of_the_gate_again():
    d, _, _ = saved_gate()
    server = loaded(d)
    bars = [c for c in server.log if c.startswith("fill") and c.endswith("iron_bars")]
    assert bars[-2:] == ["fill 7 64 10 7 66 10 minecraft:iron_bars", "fill 8 64 10 8 66 10 minecraft:iron_bars"]


def test_a_gate_that_fell_before_the_save_gets_no_bars_and_no_plugin_gate():
    d, g, site = saved_gate()
    x0, x1, z0, z1 = site["footprint"]
    d["players"]["1"]["razed"] = {combat.target_uuid([x0, z0, x1, z1]): "PALISADE_GATE"}
    server = loaded(d)
    assert not any(c.startswith("aoe gate") for c in server.log)
    assert not any(c.endswith("iron_bars") for c in server.log)


def test_a_load_on_a_vanilla_server_sends_no_plugin_gate():
    d, _, _ = saved_gate(paper=False)
    server = loaded(d, paper=False)
    assert not any(c.startswith("aoe gate") for c in server.log)
