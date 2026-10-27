package aoe2mc;

import java.util.HashMap;
import java.util.Map;

/**
 * The AoE2 rule of the attack alerts (#1231): one alert of a kind (units, buildings) for a team per place, no new alert
 * within SECONDS and BLOCKS of the last alert of that team and kind. No Bukkit: tests/test_alerts.py compiles it alone.
 */
final class AlertRule {
    static final int SECONDS = 20;
    static final double BLOCKS = 20;
    private final Map<String, double[]> last = new HashMap<>();          // team and kind -> x, z, tick of the last alert

    /** True when a hit on a unit or building (kind) of the team at x, z at this server tick gives an alert. */
    boolean due(String team, String kind, double x, double z, long tick) {
        double[] l = last.get(team + " " + kind);
        if (l != null && tick - l[2] < SECONDS * 20L && Math.hypot(x - l[0], z - l[1]) < BLOCKS) {
            return false;
        }
        last.put(team + " " + kind, new double[] {x, z, tick});
        return true;
    }
}
