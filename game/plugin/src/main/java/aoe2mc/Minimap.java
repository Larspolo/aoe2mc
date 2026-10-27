package aoe2mc;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.World;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.MapMeta;
import org.bukkit.map.MapCanvas;
import org.bukkit.map.MapRenderer;
import org.bukkit.map.MapView;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;

import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The live units on the map item of the live replay (#1237, game/replay.py): "aoe minimap on|off". With the minimap
 * on, a renderer on map 0 (the map of the converter, aoe2mc.write_map) draws a dot of DOT × DOT pixels for each living
 * entity in a team with a color (the teams of the players, aoe2mc.team_lines), once per PERIOD ticks. The dot has the
 * map color of the player (COLORS, as aoe2mc.map_objects): a live unit looks as a start unit. Animals and Gaia have no
 * team: no dot. The base image of the map stays: the default renderer draws it, and the pixels of this renderer that
 * have no dot are transparent. The server renders a map only when its data changed, and map 0 is locked: so a task
 * sends the map (Player.sendMap) to each player who holds it, once per PERIOD.
 * "aoe minimap pixel X Z" gives the map pixel of block (X, Z), or "outside" (the place rule, for the tests).
 * "aoe minimap building X0 Z0 X1 Z1 TEAM" adds the footprint (X1, Z1 exclusive) of a building of the replay in the map
 * color of the team, "aoe minimap unbuild X0 Z0" removes it (#1238). The squares are under the unit dots.
 */
final class Minimap extends MapRenderer {
    static final int PERIOD = 20;                         // ticks between two updates of the dots (sendMap)
    static final int DOT = 2;                             // pixels of a dot side
    // the team color (units.TEAM_COLOR) -> the map color ID of the player color (aoe2mc.MAP_DYES); byte: ID × 4 + 2
    static final Map<NamedTextColor, Integer> COLORS = Map.of(NamedTextColor.BLUE, 25, NamedTextColor.RED, 28,
            NamedTextColor.DARK_GREEN, 27, NamedTextColor.YELLOW, 18, NamedTextColor.AQUA, 23,
            NamedTextColor.DARK_PURPLE, 24, NamedTextColor.GRAY, 21, NamedTextColor.GOLD, 15, NamedTextColor.WHITE, 22);
    private boolean on;
    private long last = Long.MIN_VALUE;                   // the server tick of the last update
    private List<int[]> dots = new ArrayList<>();         // {px, pz} of the drawn dots and squares
    private final Map<List<Integer>, int[]> buildings = new LinkedHashMap<>();   // (x0, z0) -> {x0, z0, x1, z1, color}
    private MapView view;
    private BukkitTask task;
    private final JavaPlugin plugin;

    Minimap(JavaPlugin plugin) {
        super(false);                                     // the same image for each player
        this.plugin = plugin;
    }

    /** The map pixel (0 to 127) of block coordinate b on a map of this center and scale, or -1 outside (the rule of
     * the server and of aoe2mc.map_objects: pixel 0 starts at center - 64 × 2^scale). */
    static int pixel(double b, int center, int scale) {
        int f = 1 << scale;
        int p = (int) Math.floor((b - (center - 64 * f)) / f);
        return p >= 0 && p < 128 ? p : -1;
    }

    @SuppressWarnings("deprecation")
    private MapView view() {
        if (view == null) {
            view = Bukkit.getMap(0);
        }
        return view;
    }

    boolean command(CommandSender sender, String[] args) {
        MapView v = view();
        if (v == null) {
            sender.sendMessage("Minimap: no map 0");
            return true;
        }
        if (args.length == 4 && args[1].equals("pixel")) {
            int s = v.getScale().getValue();
            int px = pixel(Double.parseDouble(args[2]), v.getCenterX(), s);
            int pz = pixel(Double.parseDouble(args[3]), v.getCenterZ(), s);
            sender.sendMessage("Minimap pixel: " + (px < 0 || pz < 0 ? "outside" : px + " " + pz));
            return true;
        }
        if (args.length == 7 && args[1].equals("building")) {
            Team team = Bukkit.getScoreboardManager().getMainScoreboard().getTeam(args[6]);
            int c = team != null && team.hasColor() && team.color() instanceof NamedTextColor n ? COLORS.getOrDefault(n, 8) : 8;
            int[] r = {Integer.parseInt(args[2]), Integer.parseInt(args[3]), Integer.parseInt(args[4]),
                Integer.parseInt(args[5]), c * 4 + 2};
            buildings.put(List.of(r[0], r[1]), r);
            sender.sendMessage("Minimap buildings: " + buildings.size());
            return true;
        }
        if (args.length == 4 && args[1].equals("unbuild")) {
            buildings.remove(List.of(Integer.parseInt(args[2]), Integer.parseInt(args[3])));
            sender.sendMessage("Minimap buildings: " + buildings.size());
            return true;
        }
        on = args[1].equals("on");
        if (on && !v.getRenderers().contains(this)) {
            v.addRenderer(this);
            task = Bukkit.getScheduler().runTaskTimer(plugin, () -> send(v), 1L, PERIOD);
        }
        if (!on && task != null) {
            task.cancel();
            task = null;
            v.removeRenderer(this);
            dots.clear();
            last = Long.MIN_VALUE;
            send(v);                                      // the map without the dots
        }
        sender.sendMessage("Minimap: " + (on ? "on" : "off"));
        return true;
    }

    /** Send map v to each player who holds it (main or off hand): it renders the map again for that player. */
    private static void send(MapView v) {
        for (Player p : Bukkit.getOnlinePlayers()) {
            ItemStack[] hands = {p.getInventory().getItemInMainHand(), p.getInventory().getItemInOffHand()};
            for (ItemStack item : hands) {
                if (item.getItemMeta() instanceof MapMeta m && m.hasMapView() && m.getMapView().getId() == v.getId()) {
                    p.sendMap(v);
                    break;
                }
            }
        }
    }

    @Override
    @SuppressWarnings("deprecation")                      // setPixel: the exact map color byte of the converter
    public void render(MapView map, MapCanvas canvas, Player player) {
        long now = Bukkit.getCurrentTick();
        if (!on || now == last) {                         // the canvas is shared: draw once per tick
            return;
        }
        last = now;
        for (int[] d : dots) {                            // clear the old dots: the base image shows again
            canvas.setPixel(d[0], d[1], (byte) -1);
        }
        dots = new ArrayList<>();
        World world = map.getWorld() != null ? map.getWorld() : Bukkit.getWorlds().get(0);
        Scoreboard board = Bukkit.getScoreboardManager().getMainScoreboard();
        int s = map.getScale().getValue();
        for (int[] b : buildings.values()) {              // the buildings first: the dots go on top
            int px0 = Math.max(0, pixel(b[0], map.getCenterX(), s)), pz0 = Math.max(0, pixel(b[1], map.getCenterZ(), s));
            int px1 = pixel(b[2] - 1, map.getCenterX(), s), pz1 = pixel(b[3] - 1, map.getCenterZ(), s);
            for (int px = px0; px <= px1; px++) {
                for (int pz = pz0; pz <= pz1; pz++) {
                    canvas.setPixel(px, pz, (byte) b[4]);
                    dots.add(new int[] {px, pz});
                }
            }
        }
        for (LivingEntity e : world.getLivingEntities()) {
            if (e instanceof Player) {
                continue;
            }
            Team team = board.getEntityTeam(e);
            if (team == null || !team.hasColor() || !(team.color() instanceof NamedTextColor c)) {
                continue;
            }
            Location at = e.getLocation();
            int px = pixel(at.getX(), map.getCenterX(), s), pz = pixel(at.getZ(), map.getCenterZ(), s);
            if (px < 0 || pz < 0) {
                continue;
            }
            byte color = (byte) (COLORS.getOrDefault(c, 8) * 4 + 2);
            for (int dx = 0; dx < DOT && px + dx < 128; dx++) {
                for (int dz = 0; dz < DOT && pz + dz < 128; dz++) {
                    canvas.setPixel(px + dx, pz + dz, color);
                    dots.add(new int[] {px + dx, pz + dz});
                }
            }
        }
    }
}
