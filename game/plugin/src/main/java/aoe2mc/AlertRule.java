package aoe2mc;

import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import java.util.function.BiPredicate;

/**
 * The AoE2 rule of the attack alerts (#1231): one alert of a kind (units, buildings) for a team per place, no new alert
 * within SECONDS and BLOCKS of a recent alert of that team and kind. Each recent place counts (#3625): hits that
 * alternate between two places give one alert per place. No Bukkit: tests/test_alerts.py compiles it alone.
 * The allies of the team get the kind "ally" (#1941): one ally alert per receiving team and place.
 */
final class AlertRule {
    static final int SECONDS = 20;
    static final double BLOCKS = 20;
    private final Map<String, List<double[]>> recent = new HashMap<>();  // team and kind -> x, z, tick of the recent alerts

    /** True when a hit on a unit or building (kind) of the team at x, z at this server tick gives an alert. */
    boolean due(String team, String kind, double x, double z, long tick) {
        List<double[]> places = recent.computeIfAbsent(team + " " + kind, k -> new ArrayList<>());
        places.removeIf(l -> tick - l[2] >= SECONDS * 20L);
        for (double[] l : places) {
            if (Math.hypot(x - l[0], z - l[1]) < BLOCKS) {
                return false;
            }
        }
        places.add(new double[] {x, z, tick});
        return true;
    }

    /** The teams that get an ally alert for a hit on the team at x, z: each of the teams (of the scoreboard) that
     * is allied to it and not the team itself, when its "ally" alert is due. Sorted: the same order on each run. */
    List<String> allies(String team, Collection<String> teams, BiPredicate<String, String> allied, double x, double z,
            long tick) {
        List<String> out = new ArrayList<>();
        for (String t : new TreeSet<>(teams)) {
            if (!t.equals(team) && allied.test(team, t) && due(t, "ally", x, z, tick)) {
                out.add(t);
            }
        }
        return out;
    }
}
