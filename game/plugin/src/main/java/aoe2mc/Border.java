package aoe2mc;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.Color;
import org.bukkit.DyeColor;
import org.bukkit.FluidCollisionMode;
import org.bukkit.HeightMap;
import org.bukkit.Particle;
import org.bukkit.World;
import org.bukkit.block.Block;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.util.RayTraceResult;

/**
 * The border of the selection box (#795): after the first corner of the selection wand (game/gather.py box()), dust
 * particles in the player color draw the four edges of the rectangle from that corner to the ground that the player
 * looks at, on the ground of each column. Only that player sees them (Player#spawnParticle). The second corner ends it.
 */
final class Border {
    private record Box(int x, int z, Color color) {}

    private static final double REACH = 64;                          // blocks: the ray of the look, as Ghost.java
    private static final int MAX = 400;                              // particles of one border: a coarser step above
    private final Map<UUID, Box> boxes = new HashMap<>();
    private final Map<UUID, Block> corners = new HashMap<>();        // the last far corner of each player (#3082)

    /** aoe box PLAYER X Z DYE: the first corner (block X, Z) in the dye color; aoe box-clear PLAYER;
     *  aoe box-corner PLAYER: the block X Z of the last far corner (a check of the tests, #3082). */
    boolean command(CommandSender sender, String[] args, List<Player> players) {
        int n = 0;
        for (Player p : players) {
            switch (args[0]) {
                case "box" -> {
                    if (args.length < 5) {
                        return false;
                    }
                    Color color;
                    try {
                        color = DyeColor.valueOf(args[4].toUpperCase()).getColor();
                    } catch (IllegalArgumentException e) {
                        color = Color.WHITE;
                    }
                    boxes.put(p.getUniqueId(), new Box(Integer.parseInt(args[2]), Integer.parseInt(args[3]), color));
                    n++;
                }
                case "box-clear" -> n += boxes.remove(p.getUniqueId()) == null ? 0 : 1;
                case "box-corner" -> {
                    Block c = corners.get(p.getUniqueId());
                    sender.sendMessage(c == null ? "Corner: none" : "Corner: " + c.getX() + " " + c.getZ());
                    return true;
                }
                default -> {
                    return false;
                }
            }
        }
        sender.sendMessage("Box: " + n);
        return true;
    }

    /** Every few ticks: draw the border of each box to the block under the look of its player. */
    void tick() {
        for (var it = boxes.entrySet().iterator(); it.hasNext();) {
            var e = it.next();
            Player p = Bukkit.getPlayer(e.getKey());
            if (p == null) {
                it.remove();
                continue;
            }
            // The water surface (#2060) and the barriers are ground as in fleet.pick(); plants are not (#3082, as
            // Ghost.java): the ray of the world ignores the passable blocks, Player#rayTraceBlocks does not.
            var eye = p.getEyeLocation();
            RayTraceResult r = p.getWorld().rayTraceBlocks(eye, eye.getDirection(), REACH,
                    FluidCollisionMode.SOURCE_ONLY, true);
            Block b = r == null ? null : r.getHitBlock();
            if (b == null) {
                continue;
            }
            corners.put(p.getUniqueId(), b);
            Box box = e.getValue();
            int x0 = Math.min(box.x(), b.getX()), x1 = Math.max(box.x(), b.getX()) + 1;   // the cells of both corners
            int z0 = Math.min(box.z(), b.getZ()), z1 = Math.max(box.z(), b.getZ()) + 1;   // are in the box
            double step = Math.max(0.5, 2.0 * (x1 - x0 + z1 - z0) / MAX);
            var dust = new Particle.DustOptions(box.color(), 1.0f);
            World w = p.getWorld();
            for (double t = 0; t <= x1 - x0; t += step) {
                dot(p, w, x0 + t, z0, dust);
                dot(p, w, x0 + t, z1, dust);
            }
            for (double t = 0; t <= z1 - z0; t += step) {
                dot(p, w, x0, z0 + t, dust);
                dot(p, w, x1, z0 + t, dust);
            }
        }
    }

    /** One dust particle on the ground at (x, z): above the top block that is not leaves. */
    private static void dot(Player p, World w, double x, double z, Particle.DustOptions dust) {
        int bx = (int) Math.floor(x), bz = (int) Math.floor(z);
        double y = w.getHighestBlockYAt(bx, bz, HeightMap.MOTION_BLOCKING_NO_LEAVES) + 1.1;
        p.spawnParticle(Particle.DUST, x, y, z, 1, 0, 0, 0, 0, dust);
    }
}
