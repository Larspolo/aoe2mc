package aoe2mc;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.List;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Projectile;

// The kill log of the AoE2 achievements (#5640, game/achievements.py kills): AoePlugin.harm and dotHurt add each unit
// that their hit kills, with its killer. "aoe kills" gives the oldest kills (at most TAKE) and removes them from the log.
// A kill is "<side> <unit> <side> <unit>": the killer, then the killed unit. The side is the team (p<N>) or "-". The unit
// is t<ID> of its type tag aoe2mc.t<ID> (units.make_entity: on the unit, on the rider of a horse, on the crew of a ship or
// siege unit), else the UUID (a building: its target entity, game/combat.py target_uuid), or "-" with no killer.
// Minecraft has no killer of a mob that a mob kills (getKiller() is a player only, and the plugin sets the hit points).
final class Kills {
    static final int MAX = 1000;          // no game program reads the log (a plain server): only the last kills stay
    static final int TAKE = 100;          // one RCON answer stays short
    private final Deque<String> log = new ArrayDeque<>();

    void add(Entity from, Entity victim) {
        log.addLast(name(from) + " " + name(victim));
        while (log.size() > MAX) {
            log.removeFirst();
        }
    }

    boolean command(CommandSender sender) {
        StringBuilder out = new StringBuilder("Kills:");
        for (int i = 0; i < TAKE && !log.isEmpty(); i++) {
            out.append(i == 0 ? " " : "; ").append(log.removeFirst());
        }
        sender.sendMessage(out.toString());
        return true;
    }

    // The side and the unit of entity e (see above). The shooter of a projectile is the killer.
    static String name(Entity e) {
        if (e instanceof Projectile p && p.getShooter() instanceof Entity shooter) {
            e = shooter;
        }
        if (e == null) {
            return "- -";
        }
        List<Entity> near = new ArrayList<>(List.of(e));
        near.addAll(e.getPassengers());
        if (e.getVehicle() != null) {
            near.add(e.getVehicle());
            near.addAll(e.getVehicle().getPassengers());
        }
        String side = null, unit = null;
        for (Entity n : near) {
            side = side != null ? side : AoePlugin.side(n);
            for (String tag : unit == null ? n.getScoreboardTags() : List.<String>of()) {
                if (tag.matches("aoe2mc\\.t\\d+")) {
                    unit = tag.substring(7);
                }
            }
        }
        return (side != null ? side : "-") + " " + (unit != null ? unit : e.getUniqueId().toString());
    }
}
