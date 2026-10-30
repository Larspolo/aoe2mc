"""game/build.py: a complete town center, tower or castle site gets the target entity of combat.building (#1202): the
AoE2 hit points and its arrows, as a building of the map."""
import contextlib
import io
import json
import time

import pytest
from test_build_done import DOWN
from test_build_site import Server
from test_gather import grid

from game import build, combat, garrison, gather, run


def built(name, player=1):
    """Build `name` through the menu on a fake server, complete it, and return the game, the site and the new commands."""
    data = grid([[64] * 48 for _ in range(48)], [])
    data["objects"].append({"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0"})
    data.update(tile_size=4, level_height=1, players={"1": {"color": "blue", "arch": "western"}})
    server = Server({"Steve": {"Pos": (9.5, 64.0, 9.5), "Rotation": DOWN}, "v0": {"Pos": (40.5, 64.0, 40.5)}},
                    chosen=build.MENU.index(name) + 1)
    g = gather.Gather(server, data).setup()
    g.techs |= set(build.AGE_TECHS)
    g.stock.update(wood=2000, gold=2000, stone=2000)
    g.click("Steve")
    site, = g.sites
    site["player"] = player
    n = len(server.log)
    assert not build.rise(g, site, build.BUILD_TIMES[name] - 1)
    assert not [c for c in server.log[n:] if c.startswith("aoe building")]   # not before the site is complete
    assert build.rise(g, site, 1) and build.rise(g, site, 1)                # the second call sends no target again
    return g, site, server.log[n:]


def test_a_complete_watch_tower_site_takes_hits_and_shoots():
    g, site, _ = built("HOUSE")
    log = g.game.log
    n = len(log)
    tower = {**site, "name": "WATCH_TOWER"}                            # the menu has no watch tower yet
    build.target(g, tower)
    x0, x1, z0, z1 = tower["footprint"]
    shot, = [c for c in log[n:] if c.startswith("aoe building")]
    s = build.values(g, "WATCH_TOWER")
    assert shot.split()[2] == combat.target_uuid([x0, z0, x1, z1]) and f" ship:{s.bonus[combat.SHIP]}" in shot
    assert shot.split()[3:6] == [str(s.hp), str(s.melee), str(s.pierce)]   # hit points, melee and pierce armor
    assert f"aoe arrows {shot.split()[2]} {garrison.arrows('WATCH_TOWER', [])}" in log[n:]


def test_a_complete_town_center_site_takes_hits_and_shoots_once():
    g, site, log = built("TOWN_CENTER")
    shot, = [c for c in log if c.startswith("aoe building")]
    s = build.values(g, "TOWN_CENTER")
    assert shot.split()[3] == str(s.hp) and f" ship:{s.bonus[combat.SHIP]}" in shot
    assert any(c.startswith("summon slime") for c in log) and any(c.startswith("aoe label") for c in log)
    assert not g.forts.keys() & {shot.split()[2]}                     # an own building: no target of a click


def test_a_house_takes_hits_without_arrows_and_an_enemy_site_is_a_fort():
    g, site, log = built("HOUSE", player=2)
    shot, = [c for c in log if c.startswith("aoe building")]
    assert shot.split()[3] == str(build.values(g, "HOUSE").hp) and len(shot.split()) == 12   # hit points, armor, box
    assert not [c for c in log if c.startswith("aoe arrows")]
    uuid = shot.split()[2]
    assert uuid in g.forts and g.fort_names[uuid] == "HOUSE"


def test_a_farm_gets_no_target_and_a_mill_gets_one():
    _, _, log = built("FARM")                                         # its farmers stand on it
    assert not [c for c in log if c.startswith(("aoe building", "summon slime"))]
    g, _, log = built("MILL")                                         # the hit points of the data (#1403)
    assert [c.split()[3] for c in log if c.startswith("aoe building")] == [str(build.values(g, "MILL").hp)]


@pytest.mark.mc
def test_a_castle_that_the_game_program_built_shoots_an_enemy_on_a_server(tmp_path):
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import scenarios
    from AoE2ScenarioParser.datasets.units import UnitInfo

    import aoe2mc
    scn = scenarios.new_scenario(24)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.VILLAGER_MALE.ID, x=2.5, y=2.5)
    src = str(tmp_path / "castle.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        game.command("time set midnight")                              # zombies burn in the sun
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        g.techs |= set(build.AGE_TECHS)
        g.stock.update(build.COSTS["CASTLE"])
        x, z = 8 * 4, 8 * 4                                            # tile (8, 8): free ground
        site = build.place(g, "nobody", "CASTLE", (x + 0.5, g.map.y(x, z) + 10, z + 0.5), gather.direction(*DOWN))
        assert site
        x0, x1, z0, z1 = site["footprint"]
        zm = (z0 + z1) // 2                                            # 12 blocks east of the castle
        ey = g.map.y(x1 + 12, zm)
        game.command("team add p2")
        game.command(f'summon zombie {x1 + 12.5} {ey} {zm + 0.5} {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p2 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # pierce armor 1, many hit points
        time.sleep(3)
        assert health(game, "e") == 1000.0                             # a site does not shoot
        assert build.rise(g, site, build.BUILD_TIMES["CASTLE"])
        end = time.time() + 15
        while health(game, "e") == 1000.0:
            assert time.time() < end, "the castle did not shoot"
            time.sleep(0.2)
        s = build.values(g, "CASTLE")
        assert (1000 - health(game, "e")) % (s.attack + s.bonus.get("infantry", 0) - 1) == 0   # per arrow: pierce 1
