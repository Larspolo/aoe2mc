package aoe2mc;

import java.util.ArrayList;
import java.util.List;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.MapMeta;
import org.bukkit.map.MapCanvas;
import org.bukkit.map.MapRenderer;
import org.bukkit.map.MapView;

import net.kyori.adventure.text.Component;

/**
 * The heat map of a record as a map item (#5457, game/heatmap.py item_commands): "aoe heatmap TILE N X,Y,COLOR,SHADE ...
 * [end]". Each entry paints tile (X, Y) of the N × N tiles in map color COLOR, shade 0 (low) to 3 (high); "end" makes a
 * new map (a MapView with this renderer) and gives it as the item "Heat map: walk" to each online player (the
 * spectators of the replay). The map item and its colors are Minecraft; the plugin only paints the pixels.
 */
final class Heatmap extends MapRenderer {
    static final int[] SHADE = {3, 0, 1, 2};             // heat 0..3 -> the map shade byte, dark to bright
    private final byte[] pixels;                         // 128 × 128, row z

    private Heatmap(byte[] pixels) {
        this.pixels = pixels;
    }

    private static final List<int[]> pending = new ArrayList<>();   // {x, y, color, shade} of the commands so far

    @SuppressWarnings({"deprecation", "removal"})        // setPixel: the map color byte
    @Override
    public void render(MapView map, MapCanvas canvas, Player player) {
        for (int z = 0; z < 128; z++) {
            for (int x = 0; x < 128; x++) {
                canvas.setPixel(x, z, pixels[z * 128 + x]);
            }
        }
    }

    static boolean command(CommandSender sender, String[] args) {
        int n = Integer.parseInt(args[2]);
        boolean end = false;
        for (int i = 3; i < args.length; i++) {
            if (args[i].equals("end")) {
                end = true;
                continue;
            }
            String[] v = args[i].split(",");
            pending.add(new int[]{Integer.parseInt(v[0]), Integer.parseInt(v[1]), Integer.parseInt(v[2]),
                    Math.max(0, Math.min(3, Integer.parseInt(v[3])))});
        }
        if (!end) {
            return true;
        }
        byte[] px = new byte[128 * 128];
        java.util.Arrays.fill(px, Minimap.BLACK);
        for (int[] t : pending) {
            byte b = (byte) (t[2] * 4 + SHADE[t[3]]);
            for (int z = t[1] * 128 / n; z < Math.max(t[1] * 128 / n + 1, (t[1] + 1) * 128 / n); z++) {
                for (int x = t[0] * 128 / n; x < Math.max(t[0] * 128 / n + 1, (t[0] + 1) * 128 / n); x++) {
                    if (x < 128 && z < 128) {
                        px[z * 128 + x] = b;
                    }
                }
            }
        }
        int tiles = pending.size();
        pending.clear();
        MapView view = Bukkit.createMap(Bukkit.getWorlds().get(0));
        new ArrayList<>(view.getRenderers()).forEach(view::removeRenderer);
        view.setTrackingPosition(false);
        view.setLocked(true);
        view.addRenderer(new Heatmap(px));
        int given = 0;
        for (Player p : Bukkit.getOnlinePlayers()) {
            ItemStack item = new ItemStack(Material.FILLED_MAP);
            MapMeta meta = (MapMeta) item.getItemMeta();
            meta.setMapView(view);
            meta.displayName(Component.text("Heat map: walk"));
            item.setItemMeta(meta);
            p.getInventory().addItem(item);
            given++;
        }
        sender.sendMessage("Heat map: " + tiles + " tiles, " + given + " players");
        return true;
    }
}
