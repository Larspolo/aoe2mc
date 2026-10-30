"""game/build.py: a Bulgarian player builds the Krepost; it shoots and trains the Konnik (#1872). Fake server, and one
test on Paper."""
import contextlib
import io
import json
import time
from urllib.parse import unquote

import pytest
from test_build_menu import villager_map
from test_build_site import Server
from test_gather import grid

from game import build, combat, gather, run, train

DOWN = (0.0, 90.0)


def shown(server):
    """The names of the items of the last build menu of Steve."""
    log = list(server.log)
    start = max(i for i, c in enumerate(log) if c.startswith("aoe menu Steve Build "))
    cmds = [c for c in log[start:] if c.startswith(("aoe menu Steve Build ", "aoe menu-add Steve Build "))]
    return [unquote(x.split(":")[2]) for c in cmds for x in c.split(" ")[4:]]


def test_only_a_bulgarian_player_has_the_krepost_in_the_menu():
    server, g = villager_map()                                         # Britons
    build.open_menu(g, "Steve")
    assert "Krepost" not in shown(server) and len(shown(server)) == 2 + sum(not build.hidden(g, n) for n in build.MENU)   # (#2008)
    g.menus["Steve"]("Steve", build.MENU.index("KREPOST"), False)      # its slot: no choice
    assert not server.chosen
    server.chosen = build.MENU.index("KREPOST") + 1                    # also not with /trigger
    assert build.chosen(g, "Steve") is None
    g.data["players"]["1"]["civ"] = "BULGARIANS"
    build.open_menu(g, "Steve")
    assert "Krepost" in shown(server)
    krepost = next(it for it in build.items(g) if it[2] == "Krepost")
    assert krepost[0] == build.MENU.index("KREPOST") and krepost[3].endswith("\nNeeds the Castle Age")
    assert build.chosen(g, "Steve") == "KREPOST"


def test_a_complete_krepost_shoots_and_trains_the_konnik():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"civ": "BULGARIANS", "color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (30.5, 64.0, 30.5)}},
                    chosen=build.MENU.index("KREPOST") + 1)
    g = gather.Gather(server, data, carry=5, chop=0.25).setup()
    g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
    g.stock.update(stone=5000)
    g.click("Steve")
    site, = g.sites
    assert g.stock["stone"] == 5000 - build.COSTS["KREPOST"]["stone"]
    g.select("v0")
    g.click("Steve")
    for _ in range(6000):
        g.step()
        if site["progress"] == 1:
            break
    assert site["progress"] == 1
    shot = [c for c in server.log if c.startswith("aoe building ") and f" {combat.BUILDINGS['KREPOST'].attack} " in c]
    assert shot, [c for c in server.log if c.startswith("aoe building")]
    rect = next(r for r, n in train.homes(g).items() if n == "KREPOST")
    assert "KONNIK" in train.trains(g, train.homes(g)[rect])


@pytest.mark.mc
def test_a_krepost_from_the_menu_shoots_an_enemy_on_a_server(tmp_path):
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=2.5, y=2.5)
    src = str(tmp_path / "krepost.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    data["players"]["1"]["civ"] = "BULGARIANS"
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        game.command("time set midnight")                              # zombies burn in the sun
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.techs |= {"FEUDAL_AGE", "CASTLE_AGE"}
        g.stock.update(stone=build.COSTS["KREPOST"]["stone"])
        x, z = 8 * 4, 8 * 4                                            # tile (8, 8): free ground
        site = build.place(g, "nobody", "KREPOST", (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
        assert site and g.stock["stone"] == 0
        x0, x1, z0, z1 = site["footprint"]
        zm = (z0 + z1) // 2                                            # 12 blocks east of the Krepost: in its range
        ey = g.map.y(x1 + 12, zm)
        game.command("team add p2")
        game.command(f'summon zombie {x1 + 12.5} {ey} {zm + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p2 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # pierce armor 1, many hit points
        time.sleep(3)
        assert health(game, "e") == 1000.0                             # a site does not shoot
        assert build.rise(g, site, build.BUILD_TIMES["KREPOST"])
        end = time.time() + 15
        while health(game, "e") == 1000.0:
            assert time.time() < end, "the Krepost did not shoot"
            time.sleep(0.2)
        assert (1000 - health(game, "e")) % (combat.BUILDINGS["KREPOST"].attack - 1) == 0   # per arrow: attack - pierce 1
