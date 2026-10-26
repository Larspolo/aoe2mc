"""game/combat.py, game/train.py: the castles of the 11 classic civilizations train their unique units with the AoE2 DE
values (#712)."""
import re

import pytest
from test_train_castle import menus, setup

import units
from game import combat, train

CLASSIC = {"BYZANTINES": "CATAPHRACT", "CELTS": "WOAD_RAIDER", "CHINESE": "CHU_KO_NU", "FRANKS": "THROWING_AXEMAN",
           "GOTHS": "HUSKARL", "JAPANESE": "SAMURAI", "MONGOLS": "MANGUDAI", "SARACENS": "MAMELUKE",
           "TEUTONS": "TEUTONIC_KNIGHT", "TURKS": "JANISSARY", "VIKINGS": "BERSERK"}


def test_each_unique_unit_with_a_cost_has_values_a_time_and_an_item():
    for unit in train.UNIQUE.values():
        if unit in train.COSTS:
            assert unit in combat.STATS and unit in train.TRAIN_TIMES and unit in train.ITEMS, unit
            assert "unique" in combat.STATS[unit].classes
    assert all(train.UNIQUE[civ] == unit and unit in train.COSTS for civ, unit in CLASSIC.items())


@pytest.mark.parametrize("civ", sorted(CLASSIC))
def test_the_castle_menu_shows_the_unique_unit_with_its_cost_and_time(civ):
    unit = CLASSIC[civ]
    server, g = setup(civ, food=500, wood=500, gold=500)
    train.open_menu(g, "Steve", (12, 4))
    _, item, name = train.ITEMS[unit]
    cost = " · ".join(f"{v} {r}" for r, v in train.price(g, unit).items())   # the civilization cost (#1091)
    assert menus(server)[-1].startswith(f"aoe menu Steve Castle 0:{item}:{name}:{cost} · {train.TRAIN_TIMES[unit]} s")


@pytest.mark.parametrize("civ", sorted(CLASSIC))
def test_a_trained_unique_unit_has_the_converter_look_and_the_aoe2_values(civ):
    unit = CLASSIC[civ]
    server, g = setup(civ, food=500, wood=500, gold=500)
    rect = train.open_menu(g, "Steve", (12, 4))
    assert train.order(g, "Steve", rect, 0) == 1
    uuid, = train.tick(g, train.TRAIN_TIMES[unit])
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(rf"summon {units.classify(unit)['id']} ", summon)
    assert train.ITEMS[unit][1] == units.classify(unit)["id"].split(":")[1] + "_spawn_egg"
    assert combat.stats_command(uuid, unit, train.stats(g, unit)) in server.log   # with the civilization bonus (#1090)
    ranged = combat.range_command(uuid, unit, 1, s=train.stats(g, unit))
    assert (ranged in server.log) if combat.STATS[unit].range else ranged is None


def test_the_samurai_gets_its_bonus_against_unique_units():
    assert combat.damage("SAMURAI", "CATAPHRACT") == 10 - 2 + 10
    assert combat.damage("SAMURAI", "MILITIA") == 10
    assert combat.damage("CATAPHRACT", "HUSKARL") == 9 + 13
    assert combat.damage("MAMELUKE", "KNIGHT") == 8 - 2 + 9         # a ranged unit hits the pierce armor here


@pytest.mark.mc
def test_the_classic_unique_units_exist_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    if not mojang_reachable():
        pytest.skip("Mojang is not reachable")
    import contextlib
    import io
    import json

    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo

    from game import gather, run
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.CASTLE.ID, x=5, y=5)   # population 20
    src = str(tmp_path / "castle.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        answers, command = [], game.command
        game.command = lambda c: answers.append((c, command(c))) or answers[-1][1]
        for civ, name in sorted(CLASSIC.items()):
            data["players"]["1"]["civ"] = civ
            g = gather.Gather(game, data, tick=0.25, start={}).setup()
            g.techs.update(train.build.AGE_TECHS[:2])                    # the Castle Age (#1082)
            g.stock.update(food=500, wood=500, gold=500)
            rect, = [r for r, b in train.homes(g).items() if b == "CASTLE"]
            answers.clear()
            assert train.queue(g, "nobody", rect[::2], name)
            uuid, = train.tick(g, train.TRAIN_TIMES[name])
            assert g.pos(uuid) and g.soldiers == {uuid: name}, f"the trained {name} exists"
            bad = [(c, a) for c, a in answers if c.startswith(("summon", "aoe stats", "aoe range"))
                   and re.search(r"Unknown|Incorrect|Invalid|Usage|Expected", a)]
            assert not bad, bad
            game.command(f"kill {uuid}")                               # room for the next one
