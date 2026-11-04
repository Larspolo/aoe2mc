package aoe2mc;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.Color;
import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.block.Block;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.scoreboard.Team;

import io.papermc.paper.event.player.PlayerArmSwingEvent;

/**
 * The selection box with a held left click, as in AoE2 (#5759). The vanilla client swings the arm on each tick while
 * the player holds the left button on a block (Minecraft#continueAttack), and Paper fires PlayerArmSwingEvent for each
 * swing. The first swing with the command stick sets corner 1 to the ground under the look (the ray of Border.java),
 * and Border draws the box to the look. No swing for GAP ticks: the button is up. A drag in one block is a click
 * (score aoe_left 1, game/gather.py Gather.left); a larger drag sets aoe_left 2, and "aoe drag PLAYER" gives the
 * corners to game/gather.py (Gather.drag_end). The client aims only at blocks in its reach, so the reach is RANGE
 * while the player holds the command stick (also in the camera mode, Camera#reach).
 */
final class Drag implements Listener {
    private record Hold(int x, int z, long last) {}

    static final NamespacedKey REACH = new NamespacedKey("aoe2mc", "drag_reach");
    static final double RANGE = 64;                                  // blocks: the camera floor is 24 blocks up (camera.UP)
    static final long GAP = 5;                                       // ticks without a swing: the button is up (the
                                                                     // client swings each 3 ticks or less, a real drag)
    private final Map<UUID, Hold> holds = new HashMap<>();
    private final Map<UUID, Long> skips = new HashMap<>();           // a click on the air or a unit: not a drag
    private final Map<UUID, int[]> done = new HashMap<>();           // the corners of the last drag of each player
    private final Border border;
    private final Camera camera;
    private long now;

    Drag(Border border, Camera camera) {
        this.border = border;
        this.camera = camera;
    }

    /** A left click on the air or a unit (AoePlugin.onLeftClick, onHit): a click at once, its swing makes no drag. */
    void skip(Player p) {
        skips.put(p.getUniqueId(), now);
    }

    @EventHandler
    public void onSwing(PlayerArmSwingEvent ev) {
        Player p = ev.getPlayer();
        UUID id = p.getUniqueId();
        if (ev.getHand() != EquipmentSlot.HAND || !AoePlugin.commandStick(p.getInventory().getItemInMainHand())
                || now - skips.getOrDefault(id, Long.MIN_VALUE / 2) <= 1) {
            return;
        }
        Hold h = holds.get(id);
        if (h != null) {
            holds.put(id, new Hold(h.x(), h.z(), now));
            return;
        }
        Block b = Border.ground(p);
        if (b == null) {
            return;
        }
        holds.put(id, new Hold(b.getX(), b.getZ(), now));
        Team t = Bukkit.getScoreboardManager().getMainScoreboard().getEntryTeam(p.getName());
        Color c = Color.WHITE;
        if (t != null && t.hasColor() && t.color() != null) {
            c = Color.fromRGB(t.color().value());
        }
        border.start(p, b.getX(), b.getZ(), c);
    }

    /** Each tick: the reach of the players and the end of the drags. */
    void tick() {
        now++;
        for (Player p : Bukkit.getOnlinePlayers()) {
            boolean stick = AoePlugin.commandStick(p.getInventory().getItemInMainHand());
            AttributeInstance at = p.getAttribute(Attribute.BLOCK_INTERACTION_RANGE);
            if (at != null && stick != (at.getModifier(REACH) != null)) {
                at.removeModifier(REACH);
                if (stick) {
                    at.addModifier(new AttributeModifier(REACH, RANGE - at.getBaseValue(), AttributeModifier.Operation.ADD_NUMBER));
                }
                camera.reach(p, stick);
            }
        }
        for (var it = holds.entrySet().iterator(); it.hasNext();) {
            var e = it.next();
            Hold h = e.getValue();
            if (now - h.last() <= GAP) {
                continue;
            }
            it.remove();
            Player p = Bukkit.getPlayer(e.getKey());
            if (p == null) {
                continue;
            }
            border.clear(p);
            Block b = Border.ground(p);
            if (b == null || (b.getX() == h.x() && b.getZ() == h.z())) {
                AoePlugin.leftClick(p, 1);                           // one block: a click
                continue;
            }
            done.put(e.getKey(), new int[] {h.x(), h.z(), b.getX(), b.getZ()});
            AoePlugin.leftClick(p, 2);
        }
    }

    /** aoe drag PLAYER: "Drag: X0 Z0 X1 Z1", the corner blocks of the last drag (once), or "Drag: none". */
    boolean command(CommandSender sender, List<Player> players) {
        for (Player p : players) {
            int[] c = done.remove(p.getUniqueId());
            if (c != null) {
                sender.sendMessage("Drag: " + c[0] + " " + c[1] + " " + c[2] + " " + c[3]);
                return true;
            }
        }
        sender.sendMessage("Drag: none");
        return true;
    }
}
