"""The AoE2 stances work for each Minecraft mob kind of the military land units (#1950, epic #1103):
tests/test_stances.py and tests/test_stances_defensive.py test only the zombie and the skeleton."""
import math
import shutil
import time

import numpy as np
import pytest
from nbtlib import serialize_tag
from nbtlib.tag import List, String
from test_damage import health
from test_unit_ai import data

import units
from game import combat, run

T = 1                                         # blocks per tile: small lanes (sight 4 to 12 blocks)
# mob kind: one AoE2 unit of combat.STATS with an attack that the converter makes as this kind
KINDS = {"zombie": "MILITIA", "skeleton": "ARCHER", "horse": "SCOUT_CAVALRY", "skeleton_horse": "CAVALRY_ARCHER",
         "camel": "CAMEL_RIDER", "ravager": "BATTLE_ELEPHANT", "minecart": "COBRA_CAR", "drowned": "SKIRMISHER",
         "husk": "EAGLE_WARRIOR", "pillager": "HAND_CANNONEER", "zombie_villager": "FLEMISH_MILITIA",
         "creeper": "PETARD", "llama": "ALFRED_THE_ALPACA", "ocelot": "FURIOUS_THE_MONKEY_BOY", "chicken": "WAR_PENGUIN"}
NO_RETURN = {"PETARD": "it dies in its blast, as in AoE2"}   # defensive: no unit to come back


def summon(game, name, pos, tag):
    """The converter's entity of unit name (with its horse, crew or cart) at pos: tag on each part, tag + "r" on the
    root (the unit of the stats and the stance commands)."""
    nbt = units.to_nbt(units.classify(name), pos, 0.0, np.random.default_rng(sum(map(ord, tag))))
    kind = nbt.pop("id")
    nbt.pop("Pos", None)
    stack = [nbt]
    while stack:
        e = stack.pop()
        stack += list(e.get("Passengers", []))
        e.pop("UUID", None)
        e["Tags"] = List[String]([String(tag)] + [String(tag + "r")] * (e is nbt))
    return game.command(f"summon {kind} {pos[0]} {pos[1]} {pos[2]} {serialize_tag(nbt)}")


def enemy(game, pos, tag):
    game.command(f'summon zombie {pos[0]} {pos[1]} {pos[2]} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
    game.command(f"team join p2 @e[tag={tag}]")
    game.command(f"aoe stats @e[tag={tag},limit=1] 1000 0 0 0 0 infantry -")   # it lives on and does not hit


def unit(game, name, pos, tag, stance):
    assert "Summoned" in summon(game, name, pos, tag), name
    game.command(f"team join p1 @e[tag={tag}]")
    sel = f"@e[tag={tag}r,limit=1]"
    assert game.command(combat.stats_command(sel, name)).strip() == "Stats: 1 units", name
    for cmd in (combat.range_command(sel, name, T), combat.sight_command(sel, name, T)):
        if cmd:
            game.command(cmd)
    assert game.command(combat.stance_command(sel, stance)).strip() == "Stance: 1 units", name


def moved(game, tag, start):
    p = data(game, tag + "r", "Pos")
    return math.hypot(p[0] - start[0], p[2] - start[2]) if p else math.inf


def life(game, tag):
    """The hit points of the unit: its root, or the crew of a minecart."""
    h = health(game, tag + "r")
    return h if h is not None else health(game, f"{tag},type=!minecart")


def hurt(game, tag):
    return (health(game, tag) or 1000) < 1000


def arena(game, stances):
    """A floor of 56 x 50 blocks in the air per kind, and in it one unit of the kind per stance (lanes 20 blocks
    apart, more than a sight at T = 1) with an enemy: next to it (no_attack), in its sight but out of its range
    (stand_ground), in its range (defensive). Returns {kind: {stance letter: (start position)}}."""
    y = 200
    game.command("worldborder center 128 128")                 # the tiny world has a border of 96 blocks: a path
    game.command("worldborder set 400")                        # ... finder takes no step outside it (#1968)
    game.command("gamerule mobGriefing false")                 # the petard: no hole in the floor
    game.command("time set midnight")                          # the zombies do not burn
    for t in ("p1", "p2"):
        game.command(f"team add {t}")
    for i, (k, name) in enumerate(KINDS.items()):
        x0, z0 = 1 + 64 * (i % 4), 1 + 64 * (i // 4)
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 58} {z0 + 52}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 56} {y - 1} {z0 + 50} stone_bricks")
        reach = max(combat.stats(name).range * T, 2)               # the range of a melee unit: about 2 blocks
        sight = combat.sight(name) * T
        far = {"n": 2, "s": (reach + sight) / 2, "d": min(reach + 2, sight - 1)}
        for j, u in enumerate(stances):
            z = z0 + 2.5 + 20 * j
            unit(game, name, (x0 + 2.5, y, z), f"{k}{u}", STANCES[u])
            enemy(game, (x0 + 2.5 + far[u], y, z), f"{k}e{u}")
        if "n" in stances:                                     # a hit on n, as from its enemy: the rider or the crew
            hit = f"@e[tag={k}n,tag=!{k}nr,limit=1]" if units.to_nbt(units.classify(name), (0, 0, 0), 0.0,
                                                                     np.random.default_rng(0)).get("Passengers") else f"@e[tag={k}nr,limit=1]"
            before = life(game, f"{k}n")
            game.command(f"damage {hit} 1 minecraft:mob_attack by @e[tag={k}en,limit=1]")   # the plugin hits
            assert life(game, f"{k}n") < before, k                     # ... with the AoE2 attack of en
    return {k: {u: data(game, f"{k}{u}r", "Pos") for u in stances} for k in KINDS}


STANCES = {"n": "no_attack", "s": "stand_ground", "d": "defensive"}


@pytest.mark.mc
def test_no_attack_and_stand_ground_for_each_mob_kind(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        start = arena(game, "ns")
        time.sleep(15)
        fails = [f"{k} ({name}) {STANCES[u]}: hit its enemy or moved {moved(game, f'{k}{u}', start[k][u]):.1f}"
                 for k, name in KINDS.items() for u in "ns"
                 if hurt(game, f"{k}e{u}") or moved(game, f"{k}{u}", start[k][u]) > 3]
    assert not fails, "\n".join(fails)


@pytest.mark.mc
def test_defensive_for_each_mob_kind(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    with run.Game(shutil.copytree(tiny_world[0], tmp_path / "W")) as game:
        start = arena(game, "d")
        end, attacked = time.time() + 20, set()
        fighters = {k for k, name in KINDS.items() if name not in NO_RETURN}
        while time.time() < end and attacked < fighters:      # each hit when it comes: Alfred kills its enemy in 18 s
            attacked |= {k for k in fighters - attacked if hurt(game, f"{k}ed") or health(game, f"{k}ed") is None}
            time.sleep(0.5)
        for i, k in enumerate(KINDS):                          # the enemies walk away, 40 blocks
            x0, z0 = 1 + 64 * (i % 4), 1 + 64 * (i // 4)
            game.command(f"aoe moveto @e[tag={k}ed] {x0 + 50.5} 200 {z0 + 2.5}")
        time.sleep(30)
        fails = [f"{k} ({name}) defensive: " + ("did not attack the enemy in its range" if k not in attacked else
                                               f"{moved(game, f'{k}d', start[k]['d']):.1f} blocks from its place")
                 for k, name in KINDS.items() if name not in NO_RETURN
                 and (k not in attacked or moved(game, f"{k}d", start[k]["d"]) > 3)]   # as no_attack: an order ends 1.5 off
    assert not fails, "\n".join(fails)
