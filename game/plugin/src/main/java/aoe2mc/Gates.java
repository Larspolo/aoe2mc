package aoe2mc;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Mob;
import org.bukkit.util.BoundingBox;

/**
 * The gates of the game program (#1325, decision #1323: option A; a portcullis since #1656). "aoe gate TEAM X0 Y0 Z0 X1
 * Y1 Z1" adds a gate of the team: the iron bars in the box (both ends included, game/build.py portcullis). Once per
 * PERIOD ticks a gate raises its bars (air) while a unit of the team or of an allied team is within NEAR blocks or walks
 * a path through the gate, and lowers them when none is, as the AoE2 gate. A unit of a team with a gate plans its path
 * at an order with the gates of its side raised (raise()), so it walks to the gate and the gate stays open for it. An
 * enemy unit cannot plan through the bars: it walks around the wall, or it stops at the bars. A gate goes when the
 * blocks above all its bars are air (destroyed: the plugin fills the box of a destroyed building with air).
 * A second call with the same box replaces the gate (a redraw after Fortified Wall).
 * "aoe gate lock X Z" locks the gates with the block column X Z (the trigger effect "Lock Gate", #2762): their bars stay
 * down for all units, so the path finding goes around. "aoe gate unlock X Z" ends the lock.
 */
final class Gates {
    static final int PERIOD = 10;                         // ticks between two checks: a unit waits at most 0.5 s
    static final double NEAR = 2;                         // blocks around the bars (the decision #1323)
    static final int HOLD = 20;                           // ticks open after raise(): a unit without AI plans a tick later

    private record Gate(World world, String team, BoundingBox box, List<Block> bars) {}

    private final Map<String, Gate> gates = new LinkedHashMap<>();
    private final Map<String, Boolean> open = new LinkedHashMap<>();
    private final Map<String, Integer> hold = new LinkedHashMap<>();   // gate -> the tick until which raise() keeps it open
    private final Set<String> locked = new HashSet<>();   // the locked gates (#2762)

    boolean command(CommandSender sender, String[] args) {
        int[] v = new int[6];
        try {
            for (int i = 0; i < 6; i++) {
                v[i] = Integer.parseInt(args[2 + i]);
            }
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        World world = Bukkit.getWorlds().get(0);
        String key = String.join(" ", java.util.Arrays.copyOfRange(args, 2, 8));
        BoundingBox box = new BoundingBox(Math.min(v[0], v[3]), Math.min(v[1], v[4]), Math.min(v[2], v[5]),
                Math.max(v[0], v[3]) + 1, Math.max(v[1], v[4]) + 1, Math.max(v[2], v[5]) + 1);
        List<Block> bars = new ArrayList<>();
        for (int x = (int) box.getMinX(); x < box.getMaxX(); x++) {
            for (int y = (int) box.getMinY(); y < box.getMaxY(); y++) {
                for (int z = (int) box.getMinZ(); z < box.getMaxZ(); z++) {
                    Block k = world.getBlockAt(x, y, z);
                    if (k.getType() == Material.IRON_BARS) {
                        bars.add(k);
                    }
                }
            }
        }
        open.remove(key);
        if (bars.isEmpty()) {
            gates.remove(key);
        } else {
            gates.put(key, new Gate(world, args[1], box, bars));
        }
        sender.sendMessage("Gates: " + gates.size());
        return true;
    }

    /** "aoe gate lock|unlock X Z": lock or unlock the gates with the block column X Z. A locked gate lowers its bars. */
    boolean lock(CommandSender sender, String[] args) {
        boolean on = args[1].equals("lock");
        if (!on && !args[1].equals("unlock")) {
            sender.sendMessage("Usage: aoe gate lock|unlock <x> <z>");
            return true;
        }
        double x, z;
        try {
            x = Integer.parseInt(args[2]) + 0.5;
            z = Integer.parseInt(args[3]) + 0.5;
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Map.Entry<String, Gate> en : gates.entrySet()) {
            BoundingBox b = en.getValue().box();
            if (b.getMinX() <= x && x <= b.getMaxX() && b.getMinZ() <= z && z <= b.getMaxZ()) {
                n++;
                if (on && locked.add(en.getKey())) {
                    hold.remove(en.getKey());
                    set(en.getValue(), en.getKey(), false);
                } else if (!on) {
                    locked.remove(en.getKey());
                }
            }
        }
        sender.sendMessage((on ? "Locked " : "Unlocked ") + n + " gates");
        return true;
    }

    /** True when a gate exists. */
    boolean any() {
        return !gates.isEmpty();
    }

    /** Raise the closed gates of the side of the mob and its allies before it plans the path of an order: the path
     * may go through them, and tick() keeps them open while the path does. */
    void raise(Mob mob) {
        String side = AoePlugin.side(mob);
        gates.forEach((key, g) -> {
            if (AoePlugin.allied(side, g.team()) && standing(g) && !locked.contains(key)) {
                hold.put(key, Bukkit.getCurrentTick() + HOLD);
                if (!open.getOrDefault(key, false)) {
                    set(g, key, true);
                }
            }
        });
    }

    void tick() {
        gates.entrySet().removeIf(en -> {
            Gate g = en.getValue();
            if (!standing(g)) {
                open.remove(en.getKey());
                hold.remove(en.getKey());
                locked.remove(en.getKey());
                return true;
            }
            if (locked.contains(en.getKey())) {                         // the bars stay down (#2762)
                if (open.getOrDefault(en.getKey(), false)) {
                    set(g, en.getKey(), false);
                }
                return false;
            }
            BoundingBox b = g.box();
            boolean near = Bukkit.getCurrentTick() < hold.getOrDefault(en.getKey(), 0);
            for (Entity e : near ? List.<Entity>of() : g.world().getNearbyEntities(b.clone().expand(NEAR))) {
                if (e instanceof Mob m && !m.isDead() && !m.getScoreboardTags().contains("aoe2mc.building")
                        && AoePlugin.allied(AoePlugin.side(m), g.team())) {
                    near = true;
                    break;
                }
            }
            if (!near) {
                near = through(g);
            }
            if (!Boolean.valueOf(near).equals(open.get(en.getKey()))) {
                set(g, en.getKey(), near);
            }
            return false;
        });
    }

    /** True when an allied mob walks a path with a point in the gate (or next to it). */
    private boolean through(Gate g) {
        BoundingBox b = g.box().clone().expand(1);
        for (Mob m : g.world().getEntitiesByClass(Mob.class)) {
            if (m.isDead() || !AoePlugin.allied(AoePlugin.side(m), g.team())) {
                continue;
            }
            var path = m.getPathfinder().getCurrentPath();
            if (path == null) {
                continue;
            }
            for (Location p : path.getPoints()) {
                if (b.contains(p.getX() + 0.5, p.getY() + 0.5, p.getZ() + 0.5)) {
                    return true;
                }
            }
        }
        return false;
    }

    /** True while a block above a column of bars is not air: the gate stands. */
    private static boolean standing(Gate g) {
        int top = (int) g.box().getMaxY();
        for (Block k : g.bars()) {
            if (!g.world().getBlockAt(k.getX(), top, k.getZ()).getType().isAir()) {
                return true;
            }
        }
        return false;
    }

    /** Raise (open) or lower the bars of the gate, with the sound of an iron door. */
    private void set(Gate g, String key, boolean up) {
        open.put(key, up);
        int n = 0;
        for (Block k : g.bars()) {
            if (up ? k.getType() == Material.IRON_BARS : k.getType().isAir()) {
                k.setType(up ? Material.AIR : Material.IRON_BARS, true);    // physics: the bars join their neighbours
                n++;
            }
        }
        if (n > 0) {
            g.world().playSound(g.box().getCenter().toLocation(g.world()),
                    up ? Sound.BLOCK_IRON_DOOR_OPEN : Sound.BLOCK_IRON_DOOR_CLOSE, 1f, 0.6f);
        }
    }
}
