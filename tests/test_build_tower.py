"""game/build.py: the player builds a watch tower in the Feudal Age, and the complete tower shoots (#1219)."""
import contextlib
import io
import json
import time

import pytest
from test_build_done import DOWN
from test_build_site import Server
from test_gather import grid

from game import build, combat, garrison, gather, run


def test_the_menu_shows_the_watch_tower_gray_before_the_feudal_age():
    g = gather.Gather.__new__(gather.Gather)
    g.data, g.player, g.techs = {}, 1, set()
    item, = [i for i in build.items(g) if i[2] == "Watch Tower"]
    assert item[1] == build.LOCKED and "Needs the Feudal Age" in item[3]
    g.techs.add("FEUDAL_AGE")
    open_, = [i for i in build.items(g) if i[2] == "Watch Tower"]
    assert open_[1] != build.LOCKED and "Needs" not in open_[3] and item[3] == open_[3] + "\nNeeds the Feudal Age"
    assert len(build.MENU) <= 54                                       # 6 rows: the most of the plugin menu (#1873)


def test_a_complete_watch_tower_gets_its_target_and_arrows():
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (40.5, 64.0, 40.5)}},
                    chosen=build.MENU.index("WATCH_TOWER") + 1)
    g = gather.Gather(server, data).setup()
    g.techs.add("FEUDAL_AGE")
    g.stock.update(build.price(g, "WATCH_TOWER"))
    g.click("Steve")
    site, = g.sites
    assert site["name"] == "WATCH_TOWER" and g.stock["wood"] == g.stock["stone"] == 0
    assert not build.rise(g, site, build.BUILD_TIMES["WATCH_TOWER"] - 1) and build.rise(g, site, 1)
    x0, x1, z0, z1 = site["footprint"]
    uuid = combat.target_uuid([x0, z0, x1, z1])
    cmd, = [c for c in server.log if c.startswith(f"aoe building {uuid} ")]
    s = build.values(g, "WATCH_TOWER")
    assert cmd.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} ")
    assert f" {s.attack} {s.range * 4} {round(s.reload / combat.NORMAL * 20)} " in cmd          # tiles × 4, ticks
    assert f"aoe arrows {uuid} {garrison.arrows('WATCH_TOWER', [])}" in server.log


@pytest.mark.mc
def test_a_watch_tower_from_the_menu_shoots_an_enemy_on_a_server(tmp_path):
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=2.5, y=2.5)
    src = str(tmp_path / "tower.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        game.command("time set midnight")                              # zombies burn in the sun
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.techs.add("FEUDAL_AGE")
        g.stock.update(build.price(g, "WATCH_TOWER"))
        x, z = 8 * 4, 8 * 4                                            # tile (8, 8): free ground
        site = build.place(g, "nobody", "WATCH_TOWER", (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
        assert site and g.stock["wood"] == g.stock["stone"] == 0
        x0, x1, z0, z1 = site["footprint"]
        zm = (z0 + z1) // 2                                            # 12 blocks east of the tower: in its range
        ey = g.map.y(x1 + 12, zm)
        game.command("team add p2")
        game.command(f'summon zombie {x1 + 12.5} {ey} {zm + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p2 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # pierce armor 1, many hit points
        time.sleep(3)
        assert health(game, "e") == 1000.0                             # a site does not shoot
        assert build.rise(g, site, build.BUILD_TIMES["WATCH_TOWER"])
        end = time.time() + 15
        while health(game, "e") == 1000.0:
            assert time.time() < end, "the watch tower did not shoot"
            time.sleep(0.2)
        assert (1000 - health(game, "e")) % (build.values(g, "WATCH_TOWER").attack - 1) == 0   # per arrow: attack - pierce 1
