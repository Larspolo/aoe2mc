package aoe2mc;

import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.FluidCollisionMode;
import org.bukkit.GameMode;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.util.Vector;

/**
 * The follow camera of the live replay (--follow N, #738): each tick each spectator stands BACK blocks behind and UP
 * blocks above the eyes of the unit with the tag aoe2mc.followed (replay.FOLLOWED), and faces it: over its shoulder,
 * not through its eyes, so the camera is not inside the units next to it (the owner, #1660). The server cannot set
 * the F5 view of a client, so the plugin moves the spectator. A block between the unit and that point (a wall, a
 * building, its barriers) brings the camera nearer: a ray trace from the eyes of the unit. The replay moves the tag
 * to the next unit (FOLLOW_MS); a double tap of Shift (Viewer) gives adventure mode, and the camera stops following.
 */
final class Follow {
    static final String TAG = "aoe2mc.followed";
    static final double BACK = 4.0, UP = 2.0;             // blocks behind and above the eyes of the unit
    static final double GAP = 0.4;                        // blocks between the camera and a block in the way
    static final int SCAN = 20;                           // ticks between two searches when no unit has the tag
    private UUID target;
    private int wait;

    void tick() {
        var watchers = Bukkit.getOnlinePlayers().stream().filter(p -> p.getGameMode() == GameMode.SPECTATOR).toList();
        if (watchers.isEmpty()) {
            return;
        }
        Entity e = target == null ? null : Bukkit.getEntity(target);
        if (e == null || !e.isValid() || !e.getScoreboardTags().contains(TAG)) {
            if (target == null && wait-- > 0) {           // no unit had the tag: search again after SCAN ticks
                return;
            }
            e = find();                                   // at once when the tag went to the next unit
            target = e == null ? null : e.getUniqueId();
            wait = SCAN;
            if (e == null) {
                return;
            }
        }
        Location cam = camera(e);
        for (Player p : watchers) {
            if (p.getWorld() != e.getWorld()) {
                continue;
            }
            if (p.getSpectatorTarget() != null) {             // an old vanilla /spectate binds the camera
                p.setSpectatorTarget(null);
            }
            p.teleport(cam.clone().subtract(0, p.getEyeHeight(), 0));
        }
    }

    private static Entity find() {
        for (World w : Bukkit.getWorlds()) {
            for (Entity e : w.getEntities()) {
                if (e.getScoreboardTags().contains(TAG)) {
                    return e;
                }
            }
        }
        return null;
    }

    /** The eye point of the camera for unit e: behind it (its yaw) and above, nearer when a block is in the way,
     *  facing the eyes of the unit. */
    static Location camera(Entity e) {
        Location eye = e instanceof LivingEntity le ? le.getEyeLocation() : e.getLocation().add(0, e.getHeight(), 0);
        double yaw = Math.toRadians(e.getLocation().getYaw());
        Vector off = new Vector(Math.sin(yaw) * BACK, UP, -Math.cos(yaw) * BACK);   // the look is (-sin, 0, cos)
        double length = off.length();
        var hit = e.getWorld().rayTraceBlocks(eye, off.clone().normalize(), length, FluidCollisionMode.NEVER, true);
        if (hit != null) {
            length = Math.max(0.5, hit.getHitPosition().distance(eye.toVector()) - GAP);
        }
        Location cam = eye.clone().add(off.normalize().multiply(length));
        cam.setDirection(eye.toVector().subtract(cam.toVector()));
        return cam;
    }
}
