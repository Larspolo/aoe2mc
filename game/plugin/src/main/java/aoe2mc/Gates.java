package aoe2mc;

import java.util.LinkedHashMap;
import java.util.Map;

import org.bukkit.Bukkit;
import org.bukkit.Sound;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;
import org.bukkit.block.data.Openable;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Mob;
import org.bukkit.util.BoundingBox;

/**
 * The gates of the game program (#1325, decision #1323: option A). "aoe gate TEAM X0 Y0 Z0 X1 Y1 Z1" adds a gate of
 * the team: the doors in the box (both ends included, game/build.py doors). Once per PERIOD ticks a gate opens its
 * doors while a unit of the team or of an allied team is within NEAR blocks, and closes them when none is near, as the
 * AoE2 gate. A unit of a team with a gate plans its path through closed wooden doors (opens(), Pathfinder
 * setCanOpenDoors at an order): it walks to the gate, and the gate opens for it. An enemy unit cannot plan through a
 * closed door: it walks around the wall, or it stops at the doors. A gate with no door left (destroyed) goes.
 * A second call with the same box replaces the gate (a redraw after Fortified Wall).
 */
final class Gates {
    static final int PERIOD = 10;                         // ticks between two checks: a unit waits at most 0.5 s
    static final double NEAR = 2;                         // blocks around the doors (the decision #1323)

    private record Gate(World world, String team, BoundingBox doors) {}

    private final Map<String, Gate> gates = new LinkedHashMap<>();
    private final Map<String, Boolean> open = new LinkedHashMap<>();

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
        gates.put(key, new Gate(world, args[1], new BoundingBox(Math.min(v[0], v[3]), Math.min(v[1], v[4]),
                Math.min(v[2], v[5]), Math.max(v[0], v[3]) + 1, Math.max(v[1], v[4]) + 1, Math.max(v[2], v[5]) + 1)));
        open.remove(key);
        sender.sendMessage("Gates: " + gates.size());
        return true;
    }

    /** True when a gate exists: before the first one the units keep the door rule of their mob (a villager). */
    boolean any() {
        return !gates.isEmpty();
    }

    /** True when the side of the mob or an allied side has a gate: its path may go through closed wooden doors. */
    boolean opens(Mob mob) {
        String side = AoePlugin.side(mob);
        return gates.values().stream().anyMatch(g -> AoePlugin.allied(side, g.team()));
    }

    void tick() {
        gates.entrySet().removeIf(en -> {
            Gate g = en.getValue();
            BoundingBox b = g.doors();
            boolean near = false;
            for (Entity e : g.world().getNearbyEntities(b.clone().expand(NEAR))) {
                if (e instanceof Mob m && !m.isDead() && !m.getScoreboardTags().contains("aoe2mc.building")
                        && AoePlugin.allied(AoePlugin.side(m), g.team())) {
                    near = true;
                    break;
                }
            }
            int doors = 0;
            boolean change = !Boolean.valueOf(near).equals(open.put(en.getKey(), near));
            for (int x = (int) b.getMinX(); x < b.getMaxX(); x++) {
                for (int y = (int) b.getMinY(); y < b.getMaxY(); y++) {
                    for (int z = (int) b.getMinZ(); z < b.getMaxZ(); z++) {
                        Block k = g.world().getBlockAt(x, y, z);
                        BlockData d = k.getBlockData();
                        if (d instanceof Openable o) {
                            doors++;
                            if (o.isOpen() != near) {
                                o.setOpen(near);
                                k.setBlockData(o, false);
                            }
                        }
                    }
                }
            }
            if (change && doors > 0) {
                g.world().playSound(b.getCenter().toLocation(g.world()),
                        near ? Sound.BLOCK_WOODEN_DOOR_OPEN : Sound.BLOCK_WOODEN_DOOR_CLOSE, 1f, 0.6f);
            }
            if (doors == 0) {
                open.remove(en.getKey());
            }
            return doors == 0;
        });
    }
}
