"""The horse, boat or crew of a unit has the player tag (the team of the datapack pulse) and units.MOUNT, so that own
soldiers do not attack it and an area trigger counts the unit once (#1045)."""
import numpy as np
import pytest

import aoe2mc
import units


def stack(nbt):
    out, todo = [], [nbt]
    while todo:
        e = todo.pop()
        out.append(e)
        todo += list(e.get("Passengers", []))
    return out


def tags(e):
    return {str(t) for t in e.get("Tags", [])}


def test_each_entity_of_a_mounted_unit_has_the_player_tag():
    for name in ("SCOUT_CAVALRY", "KNIGHT", "CAMEL_RIDER", "WAR_ELEPHANT", "TRANSPORT_SHIP"):
        o = dict(name=name, player=2, id=448, rotation=0.0)
        nbt = units.make_entity(o, {2: {"color": "red"}}, (0.5, 0.0, 0.5), np.random.default_rng(1))
        es, top = stack(nbt), units.top_entity(nbt)
        assert len(es) > 1, name
        assert tags(top) == {"aoe2mc.p2", "aoe2mc.t448"}, name
        for e in es:
            if e is not top:
                assert tags(e) == {"aoe2mc.p2", units.MOUNT}, name


def test_a_foot_unit_gets_no_mount_tag_and_a_gaia_mount_has_the_gaia_tag():
    o = dict(name="MILITIA", player=1, id=74, rotation=0.0)
    nbt = units.make_entity(o, {}, (0.5, 0.0, 0.5), np.random.default_rng(1))
    assert tags(nbt) == {"aoe2mc.p1", "aoe2mc.t74"}
    horse = units.make_entity(dict(o, name="SCOUT_CAVALRY", player=0), {}, (0.5, 0.0, 0.5), np.random.default_rng(1))
    assert sorted(map(sorted, map(tags, stack(horse)))) == [[units.MOUNT, "aoe2mc.p0"], ["aoe2mc.p0", "aoe2mc.t74"]]


def test_an_area_trigger_skips_the_mounts():
    sel = aoe2mc.area_selector({"player": 1, "object": -1, "area": [-1, -1, -1, -1]}, 4)
    assert sel == f"@e[tag=aoe2mc.p1,tag=!{units.MOUNT}]"


@pytest.mark.mc
def test_own_soldiers_do_not_attack_a_scout_on_a_server(tmp_path):
    """As in the check #965: a militia, an archer and a scout cavalry of player 1 next to each other for 15 s."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json
    import re
    import time

    from game import combat, run
    m = {"size": 16, "terrain": [[0] * 16 for _ in range(16)], "players": {"1": {"civ": "Britons"}, "2": {}},
         "objects": [{"name": "MILITIA", "player": 1, "x": 7.5, "y": 8.5}, {"name": "ARCHER", "player": 1, "x": 8.5, "y": 8.5},
                     {"name": "SCOUT_CAVALRY", "player": 1, "x": 9.5, "y": 8.5},
                     {"name": "MILITIA", "player": 2, "x": 1.5, "y": 14.5}]}
    (tmp_path / "m.json").write_text(json.dumps(m))
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(str(tmp_path / "m.json"), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        time.sleep(5)                                                  # the datapack pulse (40 ticks) joins the teams
        assert "passed" in game.command("execute if entity @e[type=horse,team=p1]")
        assert "passed" not in game.command("execute if entity @e[type=horse,team=]")
        combat.setup(game, data)
        own = [o["uuid"] for o in data["objects"] if o["kind"] == "unit" and o["player"] == 1]

        def health():
            out = [game.command(f"data get entity {u} Health") for u in own]
            out.append(game.command("data get entity @e[type=horse,limit=1] Health"))
            return [float(re.search(r"([\d.]+)f?$", s)[1]) for s in out]
        before = health()
        time.sleep(15)
        assert health() == before
