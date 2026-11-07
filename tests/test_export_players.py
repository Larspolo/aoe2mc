"""game/export.py: the resources and the starting age of each player (#5673)."""
import contextlib
import io
import json
import shutil

import build
import export
import savegame
from AoE2ScenarioParser.datasets.object_support import StartingAge
from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario


def read(path):
    with contextlib.redirect_stdout(io.StringIO()):
        return AoE2DEScenario.from_file(str(path))


def test_save_gives_the_resources_and_the_age_at_the_end(tiny_world, tmp_path):
    world = tiny_world[0]
    save = tmp_path / "save"
    shutil.copytree(world, save / "world")
    stock = {"food": 120, "wood": 340, "gold": 55, "stone": 7}
    state = {"players": {
        "1": {"soldiers": {}, "villagers": {}, "stock": stock, "techs": [build.AGE_TECHS[0]]},
        "2": {"soldiers": {}, "villagers": {}}}}
    with open(save / savegame.FILE, "w") as f:
        json.dump(state, f)
    scn = read(export.export(str(save), str(tmp_path / "end.aoe2scenario")))
    p1 = scn.player_manager.players[1]
    assert {r: getattr(p1, r) for r in stock} == stock
    assert p1.starting_age == StartingAge.FEUDAL_AGE


def test_names_teams_diplomacy_and_ai_go_back(tmp_path):
    import scenarios
    from AoE2ScenarioParser.datasets.trigger_lists import DiplomacyState

    import aoe2mc

    src = scenarios.tiny(str(tmp_path / "t.aoe2scenario"))
    scn = read(src)
    pm = scn.player_manager
    pm.active_players = max(pm.active_players, 3)
    p1, p2, p3 = (pm.players[i] for i in (1, 2, 3))
    p1.tribe_name, p2.tribe_name = "Arthur", "Mordred"
    p1.set_player_diplomacy(3, DiplomacyState.ALLY)
    p3.set_player_diplomacy(1, DiplomacyState.ALLY)
    p2.set_player_diplomacy(3, DiplomacyState.NEUTRAL)
    p2.human, p2.ai_script, p2.population_cap, p2.lock_civ = False, "(defrule (true) => (do-nothing))", 125, True
    with contextlib.redirect_stdout(io.StringIO()):
        scn.write_to_file(str(tmp_path / "s.aoe2scenario"))
    src = tmp_path / "s.aoe2scenario"
    keys = ("team", "neutral", "name", "pop_limit", "computer", "ai", "lock_civ")

    def players(path, world):
        with contextlib.redirect_stdout(io.StringIO()):
            aoe2mc.convert(str(path), str(world))
        with open(world / "aoe2mc.json") as f:
            got = json.load(f)["players"]
        return {p: {k: v[k] for k in keys if k in v} for p, v in got.items() if p in ("1", "2", "3")}

    first = players(src, tmp_path / "A")
    assert first["1"]["team"] == first["3"]["team"] and first["2"].get("computer")
    out = export.export(str(tmp_path / "A"), str(tmp_path / "e.aoe2scenario"))
    assert players(out, tmp_path / "B") == first
