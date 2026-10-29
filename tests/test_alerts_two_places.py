"""Attack alerts at two places of one team at the same time (#3625): one alert per place, as in AoE2."""
import os
import shutil
import subprocess

import pytest

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game", "plugin", "src", "main",
                      "java", "aoe2mc")
CHECK = """package aoe2mc;
public class CheckTwo {
    public static void main(String[] a) {
        AlertRule r = new AlertRule();
        int n = 0;
        for (long t = 0; t < 400; t += 20) {                           // 20 s, one hit per second
            if (r.due("p1", "units", t % 40 == 0 ? 6 : 42, 6, t)) n++;   // alternately at x 6 and x 42
        }
        System.out.print(n);
    }
}
"""


def test_hits_that_alternate_between_two_places_give_two_alerts(tmp_path):
    javac, java = shutil.which("javac"), shutil.which("java")
    if not javac or not java:
        pytest.skip("no JDK")
    (tmp_path / "CheckTwo.java").write_text(CHECK)
    subprocess.run([javac, "-d", str(tmp_path / "c"), os.path.join(PLUGIN, "AlertRule.java"),
                    str(tmp_path / "CheckTwo.java")], check=True, capture_output=True)
    out = subprocess.run([java, "-cp", str(tmp_path / "c"), "aoe2mc.CheckTwo"], check=True, capture_output=True,
                         text=True).stdout
    assert out == "2"
