"""The ally alerts of the plugin (#1941): the allies of a team hear a horn and see "Your ally is under attack at X Z"."""
import os
import shutil
import subprocess
import time

import pytest

from game import combat, run

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game", "plugin", "src", "main",
                      "java", "aoe2mc")
CHECK = """package aoe2mc;
import java.util.List;
public class CheckAlly {
    public static void main(String[] a) {
        AlertRule r = new AlertRule();
        List<String> teams = List.of("p3", "p1", "p2");
        java.util.function.BiPredicate<String, String> allied = (x, y) -> !x.equals("p2") && !y.equals("p2");
        StringBuilder out = new StringBuilder();
        out.append(r.allies("p1", teams, allied, 0, 0, 0)).append(' ');       // the first hit on p1
        out.append(r.allies("p1", teams, allied, 10, 0, 100)).append(' ');    // 5 s later, 10 blocks away
        out.append(r.allies("p1", teams, allied, 0, 30, 140)).append(' ');    // 30 blocks away
        out.append(r.due("p1", "units", 0, 0, 140)).append(' ');              // the own alert: its own rule
        out.append(r.allies("p2", teams, allied, 0, 0, 140));                 // p2 has no ally
        System.out.print(out);
    }
}
"""


def test_the_ally_kind_has_its_own_place_rule_and_goes_only_to_allies(tmp_path):
    javac, java = shutil.which("javac"), shutil.which("java")
    if not javac or not java:
        pytest.skip("no JDK")
    (tmp_path / "CheckAlly.java").write_text(CHECK)
    subprocess.run([javac, "-d", str(tmp_path / "c"), os.path.join(PLUGIN, "AlertRule.java"),
                    str(tmp_path / "CheckAlly.java")], check=True, capture_output=True)
    out = subprocess.run([java, "-cp", str(tmp_path / "c"), "aoe2mc.CheckAlly"], check=True, capture_output=True,
                         text=True).stdout
    assert out.split() == ["[p3]", "[]", "[p3]", "true", "[]"]


def alerts(world, allies):
    """The alert lines of the server log when a castle of p2 shoots a unit of p1, with the command allies."""
    from test_damage import health
    y = 200                                    # a floor in the air, inside the world border
    box = (20, y, 20, 35, y + 40, 35)          # a castle of player 2
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")      # zombies burn in the sun
        for t in ("p1", "p2", "p3"):
            game.command(f"team add {t}")
        assert game.command(allies).startswith("Allies:")
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
            return [line.split("Alert ", 1)[1].strip() for line in f if "Alert " in line]


@pytest.mark.mc
def test_a_hit_on_p1_alerts_p1_and_its_ally_p3_not_the_enemy_p2(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    assert alerts(world, "aoe allies p1,p3") == ["p1: Your units are under attack at 48 28",
                                                 "p3: Your ally is under attack at 48 28"]
    world = shutil.copytree(tiny_world[0], tmp_path / "W2")
    assert alerts(world, "aoe allies -") == ["p1: Your units are under attack at 48 28"]     # no allies: as before
