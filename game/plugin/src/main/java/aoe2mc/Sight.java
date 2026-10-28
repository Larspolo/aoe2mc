package aoe2mc;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.Color;
import org.bukkit.HeightMap;
import org.bukkit.Particle;
import org.bukkit.World;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;

/**
 * The edge of the line of sight in the world (#3330): the fog of war hides the enemy units out of sight (game/fog.py),
 * so this edge shows where they hide and show. White dust particles stand on the ground along each side between a
 * tile in sight and an explored or unexplored tile of the fog that the player sees on the minimap (Minimap.fogOf: the
 * fog of its team, else the fog of the replay view). Only that player sees them (Player#spawnParticle, as Border.java).
 * No fog (a spectator, "polo", --reveal all): no edge. The side of a tile at the map border is no edge.
 */
final class Sight {
    static final int PERIOD = 10;                                    // ticks between two draws
    private static final double RADIUS = 48;                         // blocks around the player: the near edge only
    private static final int MAX = 1200;                             // particles of one draw: a coarser step above
    private static final Particle.DustOptions DUST = new Particle.DustOptions(Color.WHITE, 2.0f);   // seen from a high view
    private final Minimap minimap;
    private final Set<UUID> off = new HashSet<>();

    Sight(Minimap minimap) {
        this.minimap = minimap;
    }

    /** aoe sightedge PLAYERS on|off; aoe sightedge count TEAM|- X Z R: the edge sides within R blocks (checks). */
    boolean command(CommandSender sender, String[] args, List<Player> players) {
        if (args.length == 6 && args[1].equals("count")) {
            byte[][] f = minimap.fogOf(args[2].equals("-") ? null : args[2]);
            int n = sides(f, Double.parseDouble(args[3]), Double.parseDouble(args[4]), Double.parseDouble(args[5])).size();
            sender.sendMessage("Sight edge: " + n + " sides");
            return true;
        }
        if (args.length != 3 || !Set.of("on", "off").contains(args[2])) {
            return false;
        }
        for (Player p : players) {
            if (args[2].equals("off")) {
                off.add(p.getUniqueId());
            } else {
                off.remove(p.getUniqueId());
            }
        }
        sender.sendMessage("Sight edge " + args[2] + ": " + players.size() + " players");
        return true;
    }

    /** The sides {x0, z0, x1, z1} (blocks) between a tile in sight and a tile out of sight in fog f, of the tiles in
     * sight with the center within r blocks of (x, z). Each side once: from its tile in sight. */
    List<int[]> sides(byte[][] f, double x, double z, double r) {
        var out = new ArrayList<int[]>();
        int t = minimap.tile();
        if (f == null || t <= 0) {
            return out;
        }
        int n = f.length, k = (int) Math.ceil(r / t);
        int cx = (int) Math.floor(x / t), cz = (int) Math.floor(z / t);
        for (int tx = Math.max(0, cx - k); tx <= Math.min(n - 1, cx + k); tx++) {
            for (int tz = Math.max(0, cz - k); tz <= Math.min(n - 1, cz + k); tz++) {
                double dx = (tx + 0.5) * t - x, dz = (tz + 0.5) * t - z;
                if (f[tx][tz] != Minimap.SEEN || dx * dx + dz * dz > r * r) {
                    continue;
                }
                int x0 = tx * t, z0 = tz * t;
                if (tx > 0 && f[tx - 1][tz] != Minimap.SEEN) {
                    out.add(new int[] {x0, z0, x0, z0 + t});
                }
                if (tx < n - 1 && f[tx + 1][tz] != Minimap.SEEN) {
                    out.add(new int[] {x0 + t, z0, x0 + t, z0 + t});
                }
                if (tz > 0 && f[tx][tz - 1] != Minimap.SEEN) {
                    out.add(new int[] {x0, z0, x0 + t, z0});
                }
                if (tz < n - 1 && f[tx][tz + 1] != Minimap.SEEN) {
                    out.add(new int[] {x0, z0 + t, x0 + t, z0 + t});
                }
            }
        }
        return out;
    }

    /** Every PERIOD ticks: draw the near edge of the sight of each player. */
    void tick() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (off.contains(p.getUniqueId())) {
                continue;
            }
            var s = sides(minimap.fogOf(Minimap.team(p)), p.getX(), p.getZ(), RADIUS);
            if (s.isEmpty()) {
                continue;
            }
            int t = minimap.tile();
            double step = Math.max(0.5, (double) s.size() * t / MAX);
            World w = p.getWorld();
            for (int[] e : s) {
                for (double d = step / 2; d < t; d += step) {
                    dot(p, w, e[0] + (e[2] - e[0]) * d / t, e[1] + (e[3] - e[1]) * d / t);
                }
            }
        }
    }

    /** One dust particle on the ground at (x, z), above the top block that is not leaves, as Border.dot. Forced: a
     * player who looks down from high above sees it too. */
    private static void dot(Player p, World w, double x, double z) {
        int bx = (int) Math.floor(x), bz = (int) Math.floor(z);
        if (!w.isChunkLoaded(bx >> 4, bz >> 4)) {
            return;
        }
        double y = w.getHighestBlockYAt(bx, bz, HeightMap.MOTION_BLOCKING_NO_LEAVES) + 1.1;
        p.spawnParticle(Particle.DUST, x, y, z, 1, 0, 0, 0, 0, DUST, true);
    }
}
