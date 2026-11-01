package aoe2mc;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Chunk;
import org.bukkit.Location;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.block.Block;
import org.bukkit.block.data.BlockData;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerMoveEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.event.player.PlayerTeleportEvent;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import io.papermc.paper.event.packet.PlayerChunkLoadEvent;
import io.papermc.paper.math.Position;

/**
 * The camera mode of a player (owner request 2026-11-01, game/camera.py): fast walks over the map at one height, as
 * the camera of AoE2. `aoe camera <players> on <y> <x0> <z0> <x1> <z1> <speed>`: the player stands on a floor of
 * barrier blocks at y over the blocks x0..x1, z0..z1 and walks speed times the vanilla walk speed.
 * Only this player sees and feels the floor: the plugin sends its blocks to the client of the player
 * (Player#sendMultiBlockChange), and again for each chunk that the client gets later (PlayerChunkLoadEvent). The world,
 * its rain and arrows, and the other players do not change. A floor block goes only where the world has air.
 * The 26.3 server sends the real blocks under a player that stands where the server has no block (at most once in 200
 * ticks, ServerGamePacketListenerImpl#forceSendPlayerSupportBlocks, before PlayerMoveEvent): so each move sends the
 * floor under the player again (onMove), and a player that drops under the floor goes back onto it.
 * A teleport under the floor (the "Go to" menu, an alert, Alerts.view) goes up onto the floor at the same x, z and yaw,
 * and the player looks down at the place of that view.
 * In the mode the block reach of the player is 0 (the attribute block_interaction_range): the client aims at no floor
 * block, so it shows no outline and a click takes no floor block away (the server answers a click on a block with
 * the real block, air). The clicks of the game program use their own ray (gather.REACH).
 * The speed up to MAX_WALK is Player#setWalkSpeed: the client keeps its field of view. The part above MAX_WALK is the
 * attribute modifier SPEED on movement_speed: the client widens its field of view (its option "FOV Effects").
 * Vanilla has no command for the walk speed of a player and no block that only one player sees.
 * `aoe camera <players> off`: the floor goes away, the speed and the reach are normal, and the player flies UP blocks
 * above the highest block under it (the view of the "Go to" menu). `aoe camera <player>`: "Camera: on" or "Camera: off".
 */
final class Camera implements Listener {
    static final float WALK = 0.2f;                                       // the vanilla value of Player#setWalkSpeed
    static final double MAX_WALK = 5;                                     // Player#setWalkSpeed takes at most 1
    static final NamespacedKey SPEED = new NamespacedKey("aoe2mc", "camera_speed");
    static final NamespacedKey REACH = new NamespacedKey("aoe2mc", "camera_reach");
    static final double DROP = 0.01;                                     // blocks under the floor: it dropped through
    static final double HALF = 0.5;                                      // blocks around the feet: the player width and more
    private static final BlockData BARRIER = Material.BARRIER.createBlockData();
    private record Floor(int y, int x0, int z0, int x1, int z1) {}
    private final Map<UUID, Floor> floors = new HashMap<>();

    boolean command(CommandSender sender, String[] args, List<Player> players) {
        if (args.length == 2) {
            boolean on = players.stream().anyMatch(p -> floors.containsKey(p.getUniqueId()));
            sender.sendMessage("Camera: " + (on ? "on" : "off"));
            return true;
        }
        if (args.length == 3 && args[2].equals("off")) {
            long n = players.stream().filter(this::off).count();
            sender.sendMessage("Camera off: " + n + " players");
            return true;
        }
        if (args.length != 9 || !args[2].equals("on")) {
            return false;
        }
        Floor f;
        double speed;
        try {
            f = new Floor(Integer.parseInt(args[3]), Integer.parseInt(args[4]), Integer.parseInt(args[5]),
                    Integer.parseInt(args[6]), Integer.parseInt(args[7]));
            speed = Double.parseDouble(args[8]);
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Player p : players) {
            n += on(p, f, speed);
        }
        sender.sendMessage("Camera on: " + players.size() + " players, " + n + " floor blocks");
        return true;
    }

    /** Put the floor f under player p with this speed. A player in the mode only gets the new speed (and floor).
     * Returns the number of floor blocks sent. */
    private int on(Player p, Floor f, double speed) {
        Floor old = floors.put(p.getUniqueId(), f);
        if (old != null && !old.equals(f)) {
            send(p, old, false);
        }
        int n = send(p, f, true);
        p.setWalkSpeed((float) (WALK * Math.min(speed, MAX_WALK)));
        modifier(p, Attribute.MOVEMENT_SPEED, SPEED, speed > MAX_WALK ? speed / MAX_WALK - 1 : 0);
        modifier(p, Attribute.BLOCK_INTERACTION_RANGE, REACH, -1);       // the total times 0
        if (old == null) {
            Location at = p.getLocation();
            at.setY(Math.max(f.y(), p.getWorld().getHighestBlockYAt(at.getBlockX(), at.getBlockZ())) + 1);
            p.setFlying(false);                                           // it stands on the floor
            p.teleport(at);
        }
        return n;
    }

    /** End the mode of player p. False when it was not on. */
    private boolean off(Player p) {
        Floor f = floors.remove(p.getUniqueId());
        if (f == null) {
            return false;
        }
        send(p, f, false);
        reset(p);
        Location at = p.getLocation();
        at.setY(p.getWorld().getHighestBlockYAt(at.getBlockX(), at.getBlockZ()) + 1 + Alerts.UP);
        p.teleport(at);
        if (p.getAllowFlight()) {
            p.setFlying(true);                                            // creative: it stays there
        } else {
            p.addPotionEffect(new PotionEffect(PotionEffectType.SLOW_FALLING, Alerts.FALL, 0, true, false));
        }
        return true;
    }

    /** The normal walk speed and reach: also after a server stop in the mode (the walk speed is player data). */
    private static void reset(Player p) {
        p.setWalkSpeed(WALK);
        modifier(p, Attribute.MOVEMENT_SPEED, SPEED, 0);
        modifier(p, Attribute.BLOCK_INTERACTION_RANGE, REACH, 0);
    }

    /** Set the modifier key of attribute a of player p to amount (a factor - 1 of the total); 0: no modifier. */
    private static void modifier(Player p, Attribute a, NamespacedKey key, double amount) {
        AttributeInstance at = p.getAttribute(a);
        if (at == null) {
            return;
        }
        at.removeModifier(key);
        if (amount != 0) {
            at.addModifier(new AttributeModifier(key, amount, AttributeModifier.Operation.MULTIPLY_SCALAR_1));
        }
    }

    /** Send floor f (on) or the real blocks at its place (off) to the client of p, in each chunk that it has. */
    private static int send(Player p, Floor f, boolean on) {
        int n = 0;
        for (long key : p.getSentChunkKeys()) {
            int cx = (int) key, cz = (int) (key >> 32);                   // Chunk#getChunkKey
            if (p.getWorld().isChunkLoaded(cx, cz)) {
                n += send(p, f, p.getWorld().getChunkAt(cx, cz), on);
            }
        }
        return n;
    }

    private static int send(Player p, Floor f, Chunk c, boolean on) {
        int x0 = Math.max(f.x0(), c.getX() << 4), x1 = Math.min(f.x1(), (c.getX() << 4) + 15);
        int z0 = Math.max(f.z0(), c.getZ() << 4), z1 = Math.min(f.z1(), (c.getZ() << 4) + 15);
        var blocks = new HashMap<Position, BlockData>();
        for (int x = x0; x <= x1; x++) {
            for (int z = z0; z <= z1; z++) {
                Block b = c.getBlock(x & 15, f.y(), z & 15);
                if (b.getType().isAir()) {
                    blocks.put(Position.block(x, f.y(), z), on ? BARRIER : b.getBlockData());
                }
            }
        }
        if (!blocks.isEmpty()) {
            p.sendMultiBlockChange(blocks);
        }
        return blocks.size();
    }

    @EventHandler
    public void onChunk(PlayerChunkLoadEvent ev) {                        // the client got the chunk (again)
        Floor f = floors.get(ev.getPlayer().getUniqueId());
        if (f != null) {
            send(ev.getPlayer(), f, ev.getChunk(), true);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onMove(PlayerMoveEvent ev) {
        Player p = ev.getPlayer();
        Floor f = floors.get(p.getUniqueId());
        if (f == null) {
            return;
        }
        Location to = ev.getTo();
        under(p, f, to);                                                  // after the real blocks of the server
        if (!p.isFlying() && to.getY() < f.y() + 1 - DROP && inside(f, to)) {
            Location up = to.clone();                                     // it dropped through a gap: back up
            up.setY(f.y() + 1);
            ev.setTo(up);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onTeleport(PlayerTeleportEvent ev) {
        Floor f = floors.get(ev.getPlayer().getUniqueId());
        Location to = ev.getTo();
        if (f == null || to.getWorld() != ev.getPlayer().getWorld() || to.getY() >= f.y() + 1 || !inside(f, to)) {
            return;
        }
        double eye = f.y() + 1 + ev.getPlayer().getEyeHeight();          // the place: UP below, BACK in front
        to.setPitch((float) Math.toDegrees(Math.atan2(eye - (to.getY() - Alerts.UP), Alerts.BACK)));
        to.setY(f.y() + 1);
        ev.setTo(to);
    }

    private static boolean inside(Floor f, Location at) {
        return at.getX() >= f.x0() && at.getX() < f.x1() + 1 && at.getZ() >= f.z0() && at.getZ() < f.z1() + 1;
    }

    /** Send the floor blocks under the player at at (its width) to its client again. */
    private static void under(Player p, Floor f, Location at) {
        var blocks = new HashMap<Position, BlockData>();
        for (int x = (int) Math.floor(at.getX() - HALF); x <= (int) Math.floor(at.getX() + HALF); x++) {
            for (int z = (int) Math.floor(at.getZ() - HALF); z <= (int) Math.floor(at.getZ() + HALF); z++) {
                if (x >= f.x0() && x <= f.x1() && z >= f.z0() && z <= f.z1() && at.getWorld().isChunkLoaded(x >> 4, z >> 4)
                        && at.getWorld().getBlockAt(x, f.y(), z).getType().isAir()) {
                    blocks.put(Position.block(x, f.y(), z), BARRIER);
                }
            }
        }
        if (!blocks.isEmpty()) {
            p.sendMultiBlockChange(blocks);
        }
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent ev) {
        reset(ev.getPlayer());
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent ev) {
        floors.remove(ev.getPlayer().getUniqueId());
        reset(ev.getPlayer());
    }
}
