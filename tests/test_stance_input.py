"""game/stance.py: a right click on a selected military unit opens the stance menu; a click on a stance sets it for
each selected military unit, not for the villagers (#1107, owner decision A of #1106)."""
import json
import shutil
from urllib.parse import unquote

import pytest
from test_gather_attack import click
from test_select_type import setup

from game import gather, run, stance


def test_the_stance_menu_sets_the_stance_of_the_selected_soldiers():
    server, g = setup()
    click(server, g, (5.5, 13.5), (5.5, 10.5))                         # militia m-1
    click(server, g, (7.5, 5.5), (7.5, 8.5))                           # the archer: added
    g.selected.add("v-1")                                              # a villager in the selection (a box)
    assert g.selected == {"m-1", "a-1", "v-1"}
    log = click(server, g, (5.5, 13.5), (5.5, 10.5))                   # a click on the selected militia
    menu, = [unquote(c) for c in log if c.startswith("aoe menu Steve Stance ")]
    assert " 0:iron_sword:Aggressive:" in menu and "Now" in menu and " 1:shield:Defensive:" in menu
    assert " 2:iron_bars:Stand Ground:" in menu and " 3:white_banner:No Attack:" in menu
    g.menus["Steve"]("Steve", 1, False)                                # the player clicks "Defensive"
    stances = [c for c in log if c.startswith("aoe stance")]
    assert stances == ["aoe stance a-1 defensive", "aoe stance m-1 defensive"]   # not the villager
    assert "aoe menu-close Steve" in log and "Steve" not in g.menus
    assert g.stances == {"a-1": "defensive", "m-1": "defensive"}
    assert any(c.startswith("bossbar set") and json.dumps([{"translate": "aoe2mc.unit.ARCHER", "fallback": "Archer"}, " (3) · Defensive"]) in c for c in log)   # the last selected unit
    log = click(server, g, (5.5, 13.5), (5.5, 10.5))
    assert any(":shield:Defensive:" in unquote(c) and "Now" in unquote(c).split(":shield:")[1].split(" 2:")[0]
               for c in log if c.startswith("aoe menu"))
    g.menus["Steve"]("Steve", 0, False)                                # back to aggressive
    assert g.stances == {} and "aoe stance m-1 aggressive" in log


@pytest.mark.mc
def test_the_stance_menu_reads_back_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with open(world / "aoe2mc.json") as f:
        data = json.load(f)
    x, y, z = 1.5, 200, 1.5                                            # a floor in the air, inside the world border
    ids = {"s-1": "00000001-0000-0001-0000-000000000001", "s-2": "00000001-0000-0001-0000-000000000002"}
    with run.Game(world) as game:
        game.command("forceload add 0 0 8 8")
        game.command(f"fill 0 {y - 1} 0 8 {y - 1} 8 stone_bricks")
        for k, uuid in enumerate(ids.values()):
            game.command(f'summon zombie {x + 2 * k} {y} {z} {{NoAI:1b,UUID:[I;1,1,0,{k + 1}]}}')
            assert game.command(f"aoe stance {uuid}").strip() == "Stance: aggressive"
        data["objects"] += [{"kind": "unit", "name": "MILITIA", "player": 1, "uuid": u, "tile": [0.5, 0.5]}
                            for u in ids.values()]
        g = gather.Gather(game, data).setup()
        g.selected = set(ids.values())
        stance.open_menu(g, "nobody", ids["s-1"])
        g.menus["nobody"]("nobody", 2, False)                          # "Stand Ground"
        for uuid in ids.values():
            assert game.command(f"aoe stance {uuid}").strip() == "Stance: stand_ground"
