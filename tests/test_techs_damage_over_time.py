"""Damage over time of a technology (#4339): the key "damage_over_time" of data/train.jsonl (Curare, Red Cliffs Tactics)
goes into the "aoe stats" command of the units that its tests name, and the plugin deals it (Dot.java). The code tests
use test data (a monkeypatched train.BY_KEY, a rule of the building test); the menu test and the archer test take
their values from the data."""
import shutil
import time
from types import SimpleNamespace

import pytest
from test_ranged import data
from test_train_castle import menus, setup

import train as plain_train          # gather and scenario import train by its plain name (not game.train)
from game import civs, combat, run, train

CASTLE = (12, 4)
RULE = {"if": [{"names": ["ARCHER"]}], "damage": 6, "seconds": 3}


def patch(monkeypatch, entries):
    """A real technology with no damage over time gets these entries; train.stats needs a real name."""
    tech = next(t for t in sorted(train.TECHS) if t not in train.BY_KEY["damage_over_time"])
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY["damage_over_time"], tech, entries)
    return tech


def tail(command):
    """The damage, the ticks and the classes of the field dot of an "aoe stats" command (#4460), or None."""
    dot = next((w[4:] for w in command.split() if w.startswith("dot=")), None)
    return dot.split(":") if dot else None


def test_each_technology_shows_only_in_the_castle_menu_of_its_civilization():
    for tech in train.BY_KEY["damage_over_time"]:
        civ, age = train.value("civ", tech), train.value("age", tech)
        other = next(c for c in sorted(civs.UNIQUE) if c != civ)
        for who, shown in ((civ, True), (other, False)):
            server, g = setup(who, ages=age)
            train.open_menu(g, "Steve", CASTLE)
            label = train.layout(g, train.home(g, CASTLE)).get(tech, (None, None, None))[2]
            assert (label is not None and f":{label}:" in menus(server)[-1]) == shown, (tech, who)


def test_the_stats_command_has_the_damage_over_time_of_the_unit(monkeypatch):
    tech = patch(monkeypatch, [RULE, {"if": [{"names": ["MILITIA"]}], "damage": 2.5, "seconds": 1.7,
                                      "on": ["ship", "building"]}])
    server, g = setup("BRITONS")
    assert tail(train.stats_line(g, "a", "ARCHER")) is None                # not researched: none
    g.techs.add(tech)
    ticks = max(1, round(RULE["seconds"] / combat.NORMAL * 20))
    assert tail(train.stats_line(g, "a", "ARCHER")) == [f"{RULE['damage']:g}", str(ticks), "-"]
    assert tail(train.stats_line(g, "m", "MILITIA")) == ["2.5", "20", "building,ship"]
    assert tail(train.stats_line(g, "k", "KNIGHT")) is None                 # no test of the entries holds
    s = train.stats(g, "ARCHER")
    words = train.stats_line(g, "a", "ARCHER").split()
    assert words[:10] == combat.stats_command("a", "ARCHER", s).split()[:10]   # the other values stay


def test_a_research_sends_the_damage_over_time_to_the_live_units(monkeypatch):
    server, g = setup("BRITONS")
    name = next(n for n in sorted(combat.STATS) if train.stats(g, n) == combat.stats(n))   # no other change to send
    tech = patch(monkeypatch, [{"if": [{"names": [name]}], "damage": 4, "seconds": 2}])
    g.soldiers["u"] = name
    train.research(g, {"name": tech, "player": "Steve"})
    sent = [c for c in server.log if c.startswith("aoe stats u ")]
    assert sent and tail(sent[-1])[0] == "4"


@pytest.mark.mc
def test_an_archer_with_poison_hurts_a_militia_over_the_time_of_the_data(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    archer = combat.stats("ARCHER")
    tech = next((t for t in sorted(train.BY_KEY["damage_over_time"])
                 if train.dot(SimpleNamespace(techs={t}), "ARCHER", archer)), None)
    if tech is None:
        pytest.skip("no technology gives the archer damage over time")
    damage, seconds, _ = dot = train.dot(SimpleNamespace(techs={tech}), "ARCHER", archer)
    militia = combat.stats("MILITIA")._replace(hp=1000)                     # many hit points: it lives
    hit = combat.damage("ARCHER", "MILITIA", t=militia)
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 24} {z0 + 8}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 22} {y - 1} {z0 + 6} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon skeleton {x0 + 0.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["a"],'
                     'equipment:{mainhand:{id:"minecraft:bow",count:1}}}')
        game.command(f'summon zombie {x0 + 12.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command("team join p2 @e[tag=t]")
        assert game.command(combat.range_command("@e[tag=a,limit=1]", "ARCHER", 4)).strip() == "Range: 1 units"
        assert game.command(combat.stats_command("@e[tag=a,limit=1]", "ARCHER", dot=dot)).strip() == "Stats: 1 units"
        game.command(combat.stats_command("@e[tag=t,limit=1]", "MILITIA", militia))
        assert game.command("aoe attack @e[tag=a] @e[tag=t,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "t", "Health") or [1000.0])[0] >= 1000:
            time.sleep(0.05)
        game.command("aoe stop @e[tag=a]")                                  # one arrow
        first, hit_at = (data(game, "t", "Health") or [1000.0])[0], time.time()
        real = seconds / combat.NORMAL                                     # AoE2 seconds at Normal speed
        time.sleep(real / 2)
        half = (data(game, "t", "Health") or [0.0])[0]
        time.sleep(real / 2 + 1.5)
        last = (data(game, "t", "Health") or [0.0])[0]
        time.sleep(1.0)
        after = (data(game, "t", "Health") or [0.0])[0]
        log = "\n".join(game.server.log)
    assert "Entity threw exception" not in log
    assert first > 1000 - hit - damage, (first, time.time() - hit_at)       # the poison is not at once
    assert 1000 - hit - damage < half < 1000 - hit, half                  # a part of it in half the time
    assert last == pytest.approx(1000 - hit - damage), last               # all of it in the time of the data
    assert after == pytest.approx(last), after                             # and no more


@pytest.mark.mc
def test_a_building_loses_the_damage_over_time_also_after_the_attacker_died(tiny_world, tmp_path):
    from test_building_damage import hp
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    damage, seconds = 25, 5                                                # test data: a demolition ship of the Wu
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        game.command("team add p1")
        game.command("team add p2")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        game.command(f'summon husk 6.5 {y} 10.5 {{NoAI:1b,Tags:["a"]}}')
        game.command("team join p1 @e[tag=a]")
        game.command(combat.stats_command("@e[tag=a,limit=1]", "CHAMPION", dot=(damage, seconds, ("building", "ship"))))
        assert game.command(f"aoe attack @e[tag=a] {uuid}").strip() == "Attack: 1 units"
        full, end = combat.stats("HOUSE").hp, time.time() + 30
        while time.time() < end and (hp(game, uuid) or full) >= full:
            time.sleep(0.05)
        game.command("kill @e[tag=a]")                                    # one hit; a demolition ship dies too
        time.sleep(seconds / combat.NORMAL + 1.5)
        left = hp(game, uuid)
    assert left == full - combat.damage("CHAMPION", "HOUSE") - damage, left
