package aoe2mc;

import java.io.IOException;
import java.io.Reader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.BiPredicate;

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

import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;

import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The live units on the map item of the live replay (#1237, game/replay.py): "aoe minimap on|off". With the minimap
 * on, a renderer on map 0 (the map of the converter, aoe2mc.write_map) draws a dot of DOT × DOT pixels for each living
 * entity in a team with a color (the teams of the players, aoe2mc.team_lines), once per PERIOD ticks. The dot has the
 * map color of the player (COLORS, as aoe2mc.map_objects): a live unit looks as a start unit. Animals and Gaia have no
 * team: no dot, and a building target (combat.building, tag aoe2mc.building) neither (#1800). The base image of the map stays: the default renderer draws it, and the pixels of this renderer that
 * have no dot are transparent. The server renders a map only when its data changed, and map 0 is locked: so a task
 * sends the map (Player.sendMap) to each player who holds it, once per PERIOD.
 * "aoe minimap pixel X Z" gives the map pixel of block (X, Z), or "outside" (the place rule, for the tests).
 * "aoe minimap building X0 Z0 X1 Z1 TEAM" adds the footprint (X1, Z1 exclusive) of a building of the replay in the map
 * color of the team, "aoe minimap unbuild X0 Z0" removes it (#1238). The squares are under the unit dots.
 * The fog of the view player (#1567): "aoe minimap fog T N" starts it on N × N tiles of T blocks, all unexplored
 * (black); "aoe minimap see RUN ..." and "aoe minimap dim RUN ..." set tiles in sight (normal colors) and explored out
 * of sight (the darkest shade of the color), RUN = "Y,X0,X1" (tiles X0 to X1 of row Y); "aoe minimap fog off" removes
 * it. The fog goes over the base image and the buildings, under the dots. "aoe minimap tile X Z" gives the fog of
 * block (X, Z). The units that "aoe hide" hides (the enemies out of sight) have no dot.
 * The view square (#1762): "aoe minimap frame SIDE" draws a white square outline of SIDE blocks around each player
 * (the area of one AoE2 screen, game/replay.py FRAME), "aoe minimap frame off" removes it. Each player sees only the
 * own square: Frame is a contextual renderer above this one. "aoe minimap square NAME" gives the pixels of the last
 * square of player NAME (clipped at the map edge) and the map color of its first outline pixel, or "none" (the tests).
 * The bare ground (#1940): "aoe minimap on" reads "map_ground" of aoe2mc.json in the world folder (the map bytes
 * without the start objects, aoe2mc.write_objects). The renderer paints it under the buildings and the dots, so a
 * start unit that walked away or died, and a razed start building, leave no pixel. The replay sends the start
 * buildings as "aoe minimap building". Without "map_ground" (an older world) the base image shows, as before.
 * The fog of each team (#2583, the game program): "aoe minimap fog T N TEAM", "aoe minimap see TEAM RUN ...", "aoe minimap
 * dim TEAM RUN ..." and "aoe minimap fog off TEAM" set the fog of the players on TEAM (p1, p2 ...): the renderer is
 * contextual, so each player sees the fog of the own team, and the fog without a team (the replay) when the team has
 * none. With a team fog, a building square shows only after a tile of it was in sight of the team (known), as in AoE2;
 * the hidden units of a player (Player#canSee: `aoe hide` of the game program) have no dot for that player.
 * "aoe minimap tile X Z TEAM" gives the fog of the team and the pixel of the last render for a player of the team.
 * The flares of the replay (#2405): "aoe minimap flare X Z TEAM TICKS" draws a cross of FLARE pixels from the center in
 * the map color of the team at block (X, Z) for TICKS server ticks, above the dots. It blinks: on in every second
 * update. The answer names the pixel of the center, or "outside". The flares of the game program (#2676): "aoe minimap
 * flare X Z TEAM TICKS VIEWERS" with VIEWERS = the teams that see it ("p1,p3": the team of the player and its allies);
 * a player on another team does not see the cross. Without VIEWERS all players see it (the replay).
 */
final class Minimap extends MapRenderer {
    static final int PERIOD = 20;                         // ticks between two updates of the dots (sendMap)
    static final int DOT = 2;                             // pixels of a dot side
    static final int FLARE = 2;                           // pixels of an arm of the flare cross
    static final byte BLACK = 29 * 4 + 3;                 // an unexplored tile: map color COLOR_BLACK, darkest shade
    static final byte UNEXPLORED = 0, EXPLORED = 1, SEEN = 2;
    // the team color (units.TEAM_COLOR) -> the map color ID of the player color (aoe2mc.MAP_DYES); byte: ID × 4 + 2
    static final Map<NamedTextColor, Integer> COLORS = Map.of(NamedTextColor.BLUE, 25, NamedTextColor.RED, 28,
            NamedTextColor.DARK_GREEN, 27, NamedTextColor.YELLOW, 18, NamedTextColor.AQUA, 23,
            NamedTextColor.DARK_PURPLE, 24, NamedTextColor.GRAY, 21, NamedTextColor.GOLD, 15, NamedTextColor.WHITE, 22);
    private boolean on;
    private final Map<UUID, Long> last = new HashMap<>();  // player -> the server tick of its last render
    private final Map<UUID, List<int[]>> dots = new HashMap<>();   // player -> {px, pz} of the drawn dots and squares
    private final Map<List<Integer>, int[]> buildings = new LinkedHashMap<>();   // (x0, z0) -> {x0, z0, x1, z1, color}
    private final List<Flare> flares = new ArrayList<>();
    private record Flare(int x, int z, int color, long end, Set<String> viewers) {}   // viewers empty: all players
    private byte[] ground;                                // the bare ground: 128 × 128 map bytes, row z; null: none
    private byte[][] fog;                                 // [tile x][tile y] -> UNEXPLORED, EXPLORED, SEEN; null: no fog
    private int tile;                                     // blocks of a fog tile side
    private final Map<String, byte[][]> fogs = new HashMap<>();    // team -> its fog (#2583)
    private final Map<String, Set<List<Integer>>> known = new HashMap<>();   // team -> the buildings that it saw
    private final Set<UUID> fogged = new HashSet<>();     // the last render of the player drew the fog: clear all first
    private MapCanvas drawn;                              // the canvas of the last render (aoe minimap tile)
    private final Map<String, MapCanvas> drawnOf = new HashMap<>();   // team -> the canvas of its last render
    private MapView view;
    private BukkitTask task;
    private final JavaPlugin plugin;
    private final BiPredicate<Player, UUID> hidden;       // aoe hide: no dot for these units of the team of the player

    private final Frame frame = new Frame();

    Minimap(JavaPlugin plugin, BiPredicate<Player, UUID> hidden) {
        super(true);                                      // an own image for each player: the fog of its team (#2583)
        this.plugin = plugin;
        this.hidden = hidden;
    }

    /** Start the send task while the dots or the square are on, stop it when both are off. */
    private void sync(MapView v) {
        boolean run = on || frame.side > 0;
        if (run && task == null) {
            task = Bukkit.getScheduler().runTaskTimer(plugin, () -> send(v), 1L, PERIOD);
        }
        if (!run && task != null) {
            task.cancel();
            task = null;
        }
    }

    /** The square of the view of each player (#1762): a white outline of side × side blocks around the player. Each
     * player has an own canvas (a contextual renderer); all other pixels stay transparent. */
    static final class Frame extends MapRenderer {
        static final byte WHITE = 8 * 4 + 2;              // map color SNOW, the normal shade: white
        int side;                                         // blocks; 0: off
        final Map<UUID, int[]> squares = new HashMap<>();         // player -> {px0, pz0, px1, pz1} of the last render
        final Map<UUID, MapCanvas> canvases = new HashMap<>();
        final Map<UUID, List<int[]>> drawn = new HashMap<>();          // player -> the pixels of the square

        Frame() {
            super(true);                                  // an own image for each player
        }

        /** The map pixel of block coordinate b, also outside 0 to 127 (pixel() without the limit). */
        static int raw(double b, int center, int scale) {
            int f = 1 << scale;
            return (int) Math.floor((b - (center - 64 * f)) / f);
        }

        @Override
        @SuppressWarnings({"deprecation", "removal"})     // setPixel: the map color byte
        public void render(MapView map, MapCanvas canvas, Player player) {
            List<int[]> old = drawn.getOrDefault(player.getUniqueId(), List.of());
            for (int[] d : old) {                         // clear the old square: the layers below show again
                canvas.setPixel(d[0], d[1], (byte) -1);
            }
            List<int[]> now = new ArrayList<>();
            drawn.put(player.getUniqueId(), now);
            canvases.put(player.getUniqueId(), canvas);
            if (side <= 0 || map.getWorld() != null && !map.getWorld().equals(player.getWorld())) {
                squares.remove(player.getUniqueId());
                return;
            }
            int s = map.getScale().getValue();
            Location at = player.getLocation();
            double h = side / 2.0;
            int x0 = raw(at.getX() - h, map.getCenterX(), s), x1 = raw(at.getX() + h, map.getCenterX(), s);
            int z0 = raw(at.getZ() - h, map.getCenterZ(), s), z1 = raw(at.getZ() + h, map.getCenterZ(), s);
            int cx0 = Math.max(0, x0), cx1 = Math.min(127, x1), cz0 = Math.max(0, z0), cz1 = Math.min(127, z1);
            if (cx0 > cx1 || cz0 > cz1) {                 // all outside the map: no square
                squares.remove(player.getUniqueId());
                return;
            }
            squares.put(player.getUniqueId(), new int[] {cx0, cz0, cx1, cz1});
            for (int px = cx0; px <= cx1; px++) {
                for (int pz = cz0; pz <= cz1; pz++) {
                    if (px == x0 || px == x1 || pz == z0 || pz == z1) {    // only the outline, not the clip edge
                        canvas.setPixel(px, pz, WHITE);
                        now.add(new int[] {px, pz});
                    }
                }
            }
        }
    }

    /** The "map_ground" rows of aoe2mc.json in folder w or a parent of it (Paper can give the folder of the dimension),
     * or null. Streamed: the file holds the whole "ground" too. */
    static byte[] ground(Path w) {
        Path f = w.toAbsolutePath().resolve("aoe2mc.json");
        Path d = w.toAbsolutePath();
        for (int up = 0; up < 4 && d != null && !Files.isRegularFile(f); up++, d = d.getParent()) {
            f = d.resolve("aoe2mc.json");
        }
        if (!Files.isRegularFile(f)) {
            return null;
        }
        try (Reader in = Files.newBufferedReader(f); JsonReader r = new JsonReader(in)) {
            r.beginObject();
            while (r.hasNext()) {
                if (!r.nextName().equals("map_ground") || r.peek() != JsonToken.BEGIN_ARRAY) {
                    r.skipValue();
                    continue;
                }
                byte[] out = new byte[128 * 128];
                r.beginArray();
                for (int z = 0; r.hasNext(); z++) {
                    String row = r.nextString();
                    for (int x = 0; x < 128 && z < 128 && 2 * x + 2 <= row.length(); x++) {
                        out[z * 128 + x] = (byte) Integer.parseInt(row, 2 * x, 2 * x + 2, 16);
                    }
                }
                return out;
            }
        } catch (IOException | RuntimeException e) {
            return null;                                  // no bare ground: the base image shows
        }
        return null;
    }

    /** Map color c in the darkest shade (shade 3: 135/255 of the color, the map rule); no color (0 to 3): black. */
    static byte dim(byte c) {
        int id = (c & 0xFF) >> 2;
        return id == 0 ? BLACK : (byte) (id * 4 + 3);
    }

    /** The fog f at block coordinates (x, z): UNEXPLORED, EXPLORED, SEEN, or -1 without fog or outside the tiles. */
    int fogAt(byte[][] f, double x, double z) {
        int tx = (int) Math.floor(x / tile), tz = (int) Math.floor(z / tile);
        return f == null || tx < 0 || tz < 0 || tx >= f.length || tz >= f.length ? -1 : f[tx][tz];
    }

    /** The team name of player p, or null. */
    private static String team(Player p) {
        Team t = Bukkit.getScoreboardManager().getMainScoreboard().getEntryTeam(p.getName());
        return t == null ? null : t.getName();
    }

    /** True when a tile of the building rect b (x0, z0, x1, z1; x1 and z1 not in it) is in sight in fog f. */
    private boolean inSight(byte[][] f, int[] b) {
        for (int tx = Math.floorDiv(b[0], tile); tx <= Math.floorDiv(b[2] - 1, tile); tx++) {
            for (int tz = Math.floorDiv(b[1], tile); tz <= Math.floorDiv(b[3] - 1, tile); tz++) {
                if (fogAt(f, tx * tile, tz * tile) == SEEN) {
                    return true;
                }
            }
        }
        return false;
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

    @SuppressWarnings({"deprecation", "removal"})         // getPixel: the map color byte
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
        if ((args.length == 4 || args.length == 5) && args[1].equals("fog") && !args[2].equals("off")) {
            int n = Integer.parseInt(args[3]);
            tile = Math.max(1, Integer.parseInt(args[2]));
            if (args.length == 5) {                       // the fog of a team (#2583)
                fogs.put(args[4], new byte[n][n]);        // all UNEXPLORED
                known.put(args[4], new HashSet<>());
            } else {
                fog = new byte[n][n];
            }
            sender.sendMessage("Minimap fog: " + n + " tiles");
            return true;
        }
        if ((args.length == 3 || args.length == 4) && args[1].equals("fog")) {
            if (args.length == 4) {
                fogs.remove(args[3]);
                known.remove(args[3]);
            } else {
                fog = null;
            }
            sender.sendMessage("Minimap fog: off");
            return true;
        }
        if (args.length >= 3 && (args[1].equals("see") || args[1].equals("dim"))) {
            byte state = args[1].equals("see") ? SEEN : EXPLORED;
            boolean named = !args[2].contains(",");      // "see TEAM RUN ...": the fog of a team (#2583)
            byte[][] f = named ? fogs.get(args[2]) : fog;
            int n = 0;
            for (int i = named ? 3 : 2; i < args.length && f != null; i++) {
                String[] r = args[i].split(",");
                int y = Integer.parseInt(r[0]);
                for (int x = Math.max(0, Integer.parseInt(r[1])); x <= Integer.parseInt(r[2]) && x < f.length; x++) {
                    if (y >= 0 && y < f.length) {
                        f[x][y] = state;
                        n++;
                    }
                }
            }
            sender.sendMessage("Minimap " + args[1] + ": " + n + " tiles");
            return true;
        }
        if ((args.length == 4 || args.length == 5) && args[1].equals("tile")) {
            double x = Double.parseDouble(args[2]), z = Double.parseDouble(args[3]);
            MapCanvas d = args.length == 5 ? drawnOf.get(args[4]) : drawn;
            int f = fogAt(args.length == 5 ? fogs.get(args[4]) : fog, x, z), s = v.getScale().getValue();
            int px = pixel(x, v.getCenterX(), s), pz = pixel(z, v.getCenterZ(), s);
            byte c = d == null || px < 0 || pz < 0 ? 0 : d.getPixel(px, pz);
            c = c == -1 ? d.getBasePixel(px, pz) : c;     // the pixel of the last render: the layer or the base image
            sender.sendMessage("Minimap tile: " + (f < 0 ? "none" : new String[] {"unexplored", "explored", "seen"}[f])
                    + " " + (c & 0xFF));
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
        if ((args.length == 6 || args.length == 7) && args[1].equals("flare")) {
            Team team = Bukkit.getScoreboardManager().getMainScoreboard().getTeam(args[4]);
            int c = team != null && team.hasColor() && team.color() instanceof NamedTextColor n ? COLORS.getOrDefault(n, 8) : 8;
            int x = Integer.parseInt(args[2]), z = Integer.parseInt(args[3]), s = v.getScale().getValue();
            flares.add(new Flare(x, z, c * 4 + 2, Bukkit.getCurrentTick() + Long.parseLong(args[5]),
                    args.length == 7 ? Set.of(args[6].split(",")) : Set.of()));
            int px = pixel(x, v.getCenterX(), s), pz = pixel(z, v.getCenterZ(), s);
            sender.sendMessage("Minimap flare: " + (px < 0 || pz < 0 ? "outside" : px + " " + pz));
            return true;
        }
        if (args.length == 4 && args[1].equals("unbuild")) {
            List<Integer> key = List.of(Integer.parseInt(args[2]), Integer.parseInt(args[3]));
            buildings.remove(key);
            known.values().forEach(k -> k.remove(key));   // a new building at the same place is not known
            sender.sendMessage("Minimap buildings: " + buildings.size());
            return true;
        }
        if (args.length == 3 && args[1].equals("frame")) {
            frame.side = args[2].equals("off") ? 0 : Math.max(0, Integer.parseInt(args[2]));
            v.removeRenderer(frame);
            if (frame.side > 0) {
                v.addRenderer(frame);                     // the last renderer: the square is above the fog and the dots
            }
            sync(v);
            send(v);
            sender.sendMessage("Minimap frame: " + (frame.side > 0 ? frame.side + " blocks" : "off"));
            return true;
        }
        if (args.length == 3 && args[1].equals("square")) {
            Player p = Bukkit.getPlayerExact(args[2]);
            int[] q = p == null ? null : frame.squares.get(p.getUniqueId());
            List<int[]> d = q == null ? List.of() : frame.drawn.get(p.getUniqueId());
            MapCanvas c = frame.canvases.get(p == null ? null : p.getUniqueId());
            sender.sendMessage("Minimap square: " + (d.isEmpty() ? "none" : q[0] + " " + q[1] + " " + q[2] + " " + q[3]
                    + " " + (c.getPixel(d.get(0)[0], d.get(0)[1]) & 0xFF)));
            return true;
        }
        if (args.length != 2) {
            sender.sendMessage("Minimap: unknown command " + String.join(" ", args));
            return true;
        }
        on = args[1].equals("on");
        if (on) {
            World w = v.getWorld() != null ? v.getWorld() : Bukkit.getWorlds().get(0);
            ground = ground(w.getWorldFolder().toPath());
        }
        if (on && !v.getRenderers().contains(this)) {
            v.addRenderer(this);
            if (frame.side > 0) {                         // the square stays above the dots
                v.removeRenderer(frame);
                v.addRenderer(frame);
            }
        }
        if (!on && v.getRenderers().contains(this)) {
            v.removeRenderer(this);
            dots.clear();
            last.clear();
            send(v);                                      // the map without the dots
        }
        sync(v);
        sender.sendMessage("Minimap: " + (on ? "on" + (ground != null ? ", bare ground" : "") : "off"));
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
    @SuppressWarnings({"deprecation", "removal"})         // setPixel: the exact map color byte of the converter
    public void render(MapView map, MapCanvas canvas, Player player) {
        long now = Bukkit.getCurrentTick();
        UUID id = player.getUniqueId();
        if (!on || Long.valueOf(now).equals(last.get(id))) {   // draw once per tick for each player
            return;
        }
        last.put(id, now);
        drawn = canvas;
        String side = team(player);
        byte[][] fog = side != null && fogs.containsKey(side) ? fogs.get(side) : this.fog;   // the fog of its team (#2583)
        Set<List<Integer>> seen = side != null ? known.get(side) : null;      // null: all buildings show
        if (side != null) {
            drawnOf.put(side, canvas);
        }
        int s = map.getScale().getValue();
        if (ground != null) {                             // the bare ground over the whole base image (#1940)
            for (int px = 0; px < 128; px++) {
                for (int pz = 0; pz < 128; pz++) {
                    canvas.setPixel(px, pz, ground[pz * 128 + px]);
                }
            }
        } else if (fogged.contains(id)) {                 // the fog was on each pixel: clear all
            for (int px = 0; px < 128; px++) {
                for (int pz = 0; pz < 128; pz++) {
                    canvas.setPixel(px, pz, (byte) -1);
                }
            }
        } else {
            for (int[] d : dots.getOrDefault(id, List.of())) {   // clear the old dots: the base image shows again
                canvas.setPixel(d[0], d[1], (byte) -1);
            }
        }
        List<int[]> dots = new ArrayList<>();
        this.dots.put(id, dots);
        World world = map.getWorld() != null ? map.getWorld() : Bukkit.getWorlds().get(0);
        Scoreboard board = Bukkit.getScoreboardManager().getMainScoreboard();
        for (Map.Entry<List<Integer>, int[]> entry : buildings.entrySet()) {   // the buildings first: the dots go on top
            int[] b = entry.getValue();
            if (seen != null && !seen.contains(entry.getKey())) {
                if (!inSight(fog, b)) {                   // the team never saw it (#2583)
                    continue;
                }
                seen.add(entry.getKey());
            }
            int px0 = Math.max(0, pixel(b[0], map.getCenterX(), s)), pz0 = Math.max(0, pixel(b[1], map.getCenterZ(), s));
            int px1 = pixel(b[2] - 1, map.getCenterX(), s), pz1 = pixel(b[3] - 1, map.getCenterZ(), s);
            for (int px = px0; px <= px1; px++) {
                for (int pz = pz0; pz <= pz1; pz++) {
                    canvas.setPixel(px, pz, (byte) b[4]);
                    dots.add(new int[] {px, pz});
                }
            }
        }
        if (fog != null) {
            fogged.add(id);
        } else {
            fogged.remove(id);
        }
        int f = 1 << s, x0 = map.getCenterX() - 64 * f, z0 = map.getCenterZ() - 64 * f;
        for (int px = 0; px < 128 && fog != null; px++) {   // the fog of the tile at the pixel center
            for (int pz = 0; pz < 128; pz++) {
                int state = fogAt(fog, x0 + px * f + f / 2.0, z0 + pz * f + f / 2.0);
                if (state == UNEXPLORED) {
                    canvas.setPixel(px, pz, BLACK);
                } else if (state == EXPLORED) {
                    byte c = canvas.getPixel(px, pz);     // a building square, else the base image
                    canvas.setPixel(px, pz, dim(c == -1 ? canvas.getBasePixel(px, pz) : c));
                }
            }
        }
        for (LivingEntity e : world.getLivingEntities()) {
            if (e instanceof Player || hidden.test(player, e.getUniqueId()) || !player.canSee(e)   // hidden for this player
                    || e.getScoreboardTags().contains("aoe2mc.building")) {   // the target slime of a building: the
                continue;                                     // building has its square, a dot shows it in the fog (#1800)
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
        flares.removeIf(fl -> fl.end() <= now);
        for (Flare fl : flares) {                         // the flares last: above the dots, on in every second update
            if (!fl.viewers().isEmpty() && (side == null || !fl.viewers().contains(side))) {
                continue;                                 // a flare of another team (#2676)
            }
            int px = pixel(fl.x(), map.getCenterX(), s), pz = pixel(fl.z(), map.getCenterZ(), s);
            for (int k = -FLARE; k <= FLARE && px >= 0 && pz >= 0 && now / PERIOD % 2 == 0; k++) {
                for (int[] q : new int[][] {{px + k, pz}, {px, pz + k}}) {
                    if (q[0] >= 0 && q[0] < 128 && q[1] >= 0 && q[1] < 128) {
                        canvas.setPixel(q[0], q[1], (byte) fl.color());
                        dots.add(q);
                    }
                }
            }
        }
    }
}
