package aoe2mc;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.Color;
import org.bukkit.FluidCollisionMode;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.BlockDisplay;
import org.bukkit.entity.Display;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.util.RayTraceResult;
import org.bukkit.util.Transformation;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

/**
 * The ghost of the building that a player places (#794): block displays in the shape of the design follow the
 * ground that the player looks at, snapped to the tile grid as game/build.py area() does. Only that player sees
 * them. The program sends the shape and the color (green: the building can stand there, red: not).
 */
final class Ghost {
    private record Part(float x, float y, float z, BlockData block) {}

    private static final class State {
        final List<Part> parts = new ArrayList<>();
        final List<BlockDisplay> shown = new ArrayList<>();
        float scale = 1;
        int tile = 1, size = 1;
        Location at;
        Color color = Color.LIME;
    }

    private static final double REACH = 64;                          // blocks: the ray of the look
    private final JavaPlugin plugin;
    private final Map<UUID, State> ghosts = new HashMap<>();

    Ghost(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    /** aoe ghost-shape PLAYER SCALE X/Y/Z/STATE...; aoe ghost PLAYER TILE SIZE; aoe ghost-color PLAYER red|green;
     *  aoe ghost-clear PLAYER. */
    boolean command(CommandSender sender, String[] args, List<Player> players) {
        int n = 0;
        for (Player p : players) {
            UUID id = p.getUniqueId();
            switch (args[0]) {
                case "ghost-shape" -> {
                    State s = ghosts.computeIfAbsent(id, k -> new State());
                    s.scale = Float.parseFloat(args[2]);
                    for (int i = 3; i < args.length; i++) {
                        String[] t = args[i].split("/", 4);
                        try {
                            String state = t[3].contains(":") ? t[3] : "minecraft:" + t[3];
                            s.parts.add(new Part(Float.parseFloat(t[0]), Float.parseFloat(t[1]), Float.parseFloat(t[2]),
                                                 Bukkit.createBlockData(state)));
                            n++;
                        } catch (IllegalArgumentException | ArrayIndexOutOfBoundsException e) {
                            // a state that this server does not know: no block
                        }
                    }
                }
                case "ghost" -> {
                    State s = ghosts.get(id);
                    if (s == null) {
                        continue;
                    }
                    s.tile = Integer.parseInt(args[2]);
                    s.size = Integer.parseInt(args[3]);
                    hide(s);
                    for (Part part : s.parts) {
                        s.shown.add(p.getWorld().spawn(p.getLocation(), BlockDisplay.class, d -> {
                            d.setBlock(part.block());
                            d.setTransformation(new Transformation(
                                new Vector3f(part.x() * s.scale, part.y() * s.scale, part.z() * s.scale), new AxisAngle4f(),
                                new Vector3f(s.scale, s.scale, s.scale), new AxisAngle4f()));
                            d.setBrightness(new Display.Brightness(15, 15));   // not dark inside a slope
                            d.setGlowing(true);
                            d.setGlowColorOverride(s.color);
                            d.setPersistent(false);
                            d.setVisibleByDefault(false);       // only the player who places the building sees it
                            d.setTeleportDuration(2);
                        }));
                    }
                    for (BlockDisplay d : s.shown) {
                        p.showEntity(plugin, d);
                    }
                    s.at = null;
                    n += s.shown.size();
                }
                case "ghost-color" -> {
                    State s = ghosts.get(id);
                    if (s == null) {
                        continue;
                    }
                    s.color = args[2].equals("red") ? Color.RED : Color.LIME;
                    for (BlockDisplay d : s.shown) {
                        d.setGlowColorOverride(s.color);
                    }
                    n++;
                }
                case "ghost-clear" -> {
                    State s = ghosts.remove(id);
                    if (s != null) {
                        hide(s);
                        n++;
                    }
                }
                default -> {
                    return false;
                }
            }
        }
        sender.sendMessage("Ghost: " + n);
        return true;
    }

    private static void hide(State s) {
        for (BlockDisplay d : s.shown) {
            d.remove();
        }
        s.shown.clear();
    }

    /** Each tick: move each ghost to the tile under the look of its player (only when that tile changes). */
    void tick() {
        for (var it = ghosts.entrySet().iterator(); it.hasNext();) {
            var e = it.next();
            Player p = Bukkit.getPlayer(e.getKey());
            State s = e.getValue();
            if (p == null) {
                hide(s);
                it.remove();
                continue;
            }
            if (s.shown.isEmpty()) {
                continue;
            }
            // Plants, barriers and water under the look made the ghost jump to the head and back (#2053):
            // the ray stops only on the solid ground, the water surface counts as ground
            Location eye = p.getEyeLocation();
            RayTraceResult r = p.getWorld().rayTraceBlocks(eye, eye.getDirection(), REACH,
                    FluidCollisionMode.SOURCE_ONLY, true, b -> b.getType() != Material.BARRIER);
            Block b = r == null ? null : r.getHitBlock();
            if (b == null) {
                continue;
            }
            int x0 = (Math.floorDiv(b.getX(), s.tile) - s.size / 2) * s.tile;    // game/build.py area()
            int z0 = (Math.floorDiv(b.getZ(), s.tile) - s.size / 2) * s.tile;
            Location at = new Location(b.getWorld(), x0, b.getY() + 1, z0);
            if (at.equals(s.at)) {
                continue;
            }
            s.at = at;
            for (BlockDisplay d : s.shown) {
                d.teleport(at);
            }
        }
    }
}
