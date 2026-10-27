"""The attack alerts of the plugin (#1231): AlertRule (one alert of a kind per team and place) and Alerts on a server."""
import os
import shutil
import subprocess
import time

import pytest

from game import combat, run

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game", "plugin", "src", "main",
                      "java", "aoe2mc")
CHECK = """package aoe2mc;
public class CheckRule {
    public static void main(String[] a) {
        AlertRule r = new AlertRule();
        StringBuilder out = new StringBuilder();
        out.append(r.due("p1", "units", 0, 0, 0)).append(' ');            // the first hit
        out.append(r.due("p1", "units", 10, 0, 100)).append(' ');         // 5 s later, 10 blocks away
        out.append(r.due("p1", "units", 0, 30, 140)).append(' ');         // 7 s, 30 blocks away
        out.append(r.due("p1", "units", 0, 0, 500)).append(' ');          // 25 s after the first
        out.append(r.due("p1", "buildings", 0, 0, 500)).append(' ');      // a building at the same place
        out.append(r.due("p2", "units", 0, 0, 500));                      // another team
        System.out.print(out);
    }
}
"""


def test_the_rule_gives_one_alert_of_a_kind_per_place_and_20_seconds(tmp_path):
    javac, java = shutil.which("javac"), shutil.which("java")
    if not javac or not java:
        pytest.skip("no JDK")
    (tmp_path / "CheckRule.java").write_text(CHECK)
    subprocess.run([javac, "-d", str(tmp_path / "c"), os.path.join(PLUGIN, "AlertRule.java"),
                    str(tmp_path / "CheckRule.java")], check=True, capture_output=True)
    out = subprocess.run([java, "-cp", str(tmp_path / "c"), "aoe2mc.CheckRule"], check=True, capture_output=True,
                         text=True).stdout
    assert out.split() == ["true", "false", "true", "true", "true", "true"]


@pytest.mark.mc
def test_an_enemy_hit_gives_one_alert_for_the_team_of_the_unit(tiny_world, tmp_path):
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 35, y + 40, 35)          # a castle of player 2
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        game.command(f'summon zombie 48.5 {y} 28.5 {{NoAI:1b,IsBaby:0b,Tags:["e"]}}')
        game.command("team join p1 @e[tag=e]")
        assert game.command(combat.stats_command("@e[tag=e,limit=1]", "MILITIA")).strip() == "Stats: 1 units"
        game.command("aoe stats @e[tag=e,limit=1] 1000 4 0 1 0 infantry - 20")    # many hit points: many hits
        for c in combat.building(combat.target_uuid([20, 20, 36, 36]), "CASTLE", 2, box):
            game.command(c)
        end = time.time() + 20
        while health(game, "e") > 1000 - 3 * 50:                       # 3 volleys: 5 arrows of 10 each
            assert time.time() < end, "the castle did not shoot"
            time.sleep(0.2)
        with open(os.path.join(game.folder, "logs", "latest.log")) as f:
            alerts = [line for line in f if "Alert " in line]
    assert len(alerts) == 1, alerts                                    # one place, less than 20 s
    assert "Alert p1: Your units are under attack at 48 28" in alerts[0]
