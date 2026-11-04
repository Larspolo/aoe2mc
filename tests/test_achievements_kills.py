"""The achievements of one kill: the kill log of the plugin ("aoe kills", Kills.java) and the "kill" lines (#5640)."""
import os
import shutil
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import achievements  # noqa: E402

import units  # noqa: E402

ROWS = [{"name": "TREB_ON_TREB", "event": "kill", "killed": ["TREBUCHET", "TREBUCHET_PACKED"], "by": ["TREBUCHET"]},
        {"name": "TC_ON_SCOUT", "event": "kill", "killed": ["SCOUT_CAVALRY"], "by": ["TOWN_CENTER"]},
        {"name": "MELEE_ON_SHIP", "event": "kill", "killed": ["ships"], "by": ["non-ranged units+land units but siege"]}]
GRANT = "advancement grant @a[team=p1] only aoe2mc:"
TC = "0c1b2a39-0000-5000-8000-000000000001"


def t(name):
    return f"t{units.type_ids()[name]}"


def game(log, share=None, players=None):
    """Player 1 of a game; its command answers "aoe kills" with log and keeps the other commands."""
    sent = []
    g = SimpleNamespace(player=1, share=share, peers=[], bots=[], players=players or {}, fort_names={TC: "TOWN_CENTER"},
                        data={"players": {"1": {"civ": "FRANKS"}}})
    g.command = lambda c: log if c == "aoe kills" else sent.append(c)
    return g, sent


def test_each_kill_grants_its_line_once_to_the_killer(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    g, sent = game(f"Kills: p1 {t('TREBUCHET')} p2 {t('TREBUCHET_PACKED')}; p1 {TC} p2 {t('SCOUT_CAVALRY')}; "
                   f"p1 {t('MILITIA')} p2 {t('GALLEY')}; p1 {t('TREBUCHET')} p2 {t('TREBUCHET')}")
    achievements.kills(g)
    assert sent == [GRANT + k for k in ("treb_on_treb", "tc_on_scout", "melee_on_ship")]


def test_other_killers_victims_and_sides_grant_nothing(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    log = (f"Kills: p1 {t('MANGONEL')} p2 {t('TREBUCHET')}; p1 {t('TREBUCHET')} p2 {t('MANGONEL')}; "
           f"p1 {t('ARCHER')} p2 {t('GALLEY')}; p1 {t('MILITIA')} p2 {t('MILITIA')}; "     # a ranged killer, no ship
           f"p2 {t('TREBUCHET')} p1 {t('TREBUCHET')}; - - p2 {t('TREBUCHET')}; "            # the other side, no killer
           f"p1 {t('TREBUCHET')} p3 {t('TREBUCHET')}; p1 {t('TREBUCHET')} - {t('TREBUCHET')}")   # an ally, no side
    g, sent = game(log, players={"1": {"team": 1}, "3": {"team": 1}})
    achievements.kills(g)
    assert sent == []


def test_a_bot_reads_no_log_and_no_kill_line_sends_no_command(monkeypatch):
    monkeypatch.setattr(achievements, "ROWS", ROWS)
    bot, _ = game("")
    bot.share = SimpleNamespace()
    bot.command = lambda c: (_ for _ in ()).throw(AssertionError(c))
    achievements.kills(bot)
    monkeypatch.setattr(achievements, "ROWS", [{"name": "LOOMED", "event": "research LOOM"}])
    g, _ = game("")
    g.command = bot.command
    achievements.kills(g)


def test_each_kill_item_is_a_unit_a_building_or_groups():
    import civs
    import combat
    known = set(units.type_ids()) | set(combat.BUILDINGS)
    for r in achievements.ROWS:
        for item in r.get("killed", []) + r.get("by", []):
            assert item in known or all(p in civs.GROUPS for p in item.split("+")), (r["name"], item)


def unit(game, i, tag, team, hp, attack):
    """A unit with the AoE2 values, the type tag tag and the UUID ending in hex i, in team team."""
    uuid = f"00000000-0000-0000-0000-0000000000{i:02x}"
    game.command(f'summon minecraft:zombie 8 80 8 {{UUID:[I;0,0,0,{i}],NoAI:1b,Tags:["{tag}","k{i}"]}}')
    game.command(f"team join {team} {uuid}")
    game.command(f"aoe stats @e[tag=k{i},limit=1] {hp} {attack} 0 0 0 infantry - 20")
    return uuid


@pytest.mark.mc
def test_the_plugin_logs_the_killer_of_each_kill(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        game.forceload()
        for team in ("p1", "p2"):
            game.command(f"team add {team}")
        assert game.command("aoe kills").strip() == "Kills:"
        killer, victim = unit(game, 161, "aoe2mc.t42", "p1", 100, 500), unit(game, 162, "aoe2mc.t331", "p2", 10, 1)
        game.command(f"damage {victim} 1 minecraft:mob_attack by {killer}")
        other = unit(game, 163, "aoe2mc.t42", "p2", 10, 1)
        game.command(f"kill {other}")                                   # no AoE2 hit: no killer, no kill
        assert game.command("aoe kills").strip() == "Kills: p1 t42 p2 t331"
        assert game.command("aoe kills").strip() == "Kills:"            # the read removes the kills
