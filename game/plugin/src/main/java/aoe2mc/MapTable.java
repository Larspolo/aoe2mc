package aoe2mc;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.block.BlockFace;
import org.bukkit.entity.ItemFrame;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerInteractAtEntityEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.MapMeta;
import org.bukkit.map.MapView;
import org.bukkit.scoreboard.Criteria;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.util.Vector;

import net.kyori.adventure.text.Component;

/**
 * The map table (#2586, owner decision #2585: option A): the game program puts an item frame with map 0 (the map of
 * the converter, aoe2mc.write_map) on a cartography table near each own town center (game/map_table.py). A right click
 * with the command stick on a pixel of the framed map is the right click on the AoE2 minimap: the plugin turns the
 * click position on the frame into the block in the middle of that map pixel and sets the scores X and Z of the
 * player, then CLICK to 1. map_table.tick sends the selection there. Vanilla has no event for the position of a click
 * on an entity: the client sends it only in the interact packet (PlayerInteractAtEntityEvent).
 */
final class MapTable implements Listener {
    static final String CLICK = "aoe_map", X = "aoe_map_x", Z = "aoe_map_z";

    /** The block coordinate in the middle of map pixel p (0 to 127) on a map of this center and scale: the reverse
     * of Minimap.pixel. */
    static int block(int p, int center, int scale) {
        int f = 1 << scale;
        return center - 64 * f + p * f + f / 2;
    }

    /** The map pixel (0 to 127) of the position d (-0.5 to 0.5) on the frame, from its west or north edge. */
    static int pixel(double d) {
        return Math.max(0, Math.min(127, (int) Math.floor((d + 0.5) * 128)));
    }

    private static Objective score(String name) {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective(name);
        return o != null ? o : sb.registerNewObjective(name, Criteria.DUMMY, Component.text(name));
    }

    @EventHandler(ignoreCancelled = true)
    public void onClick(PlayerInteractAtEntityEvent ev) {
        Player p = ev.getPlayer();
        ItemStack hand = p.getInventory().getItemInMainHand();
        if (ev.getHand() != EquipmentSlot.HAND || !(ev.getRightClicked() instanceof ItemFrame f)
                || f.getFacing() != BlockFace.UP || f.getItem().getType() != Material.FILLED_MAP
                || !(f.getItem().getItemMeta() instanceof MapMeta m) || !m.hasMapView()
                || hand.getType() != Material.CARROT_ON_A_STICK || hand.hasItemMeta() && hand.getItemMeta().hasItemName()) {
            return;
        }
        ev.setCancelled(true);                            // no turn of the map
        MapView v = m.getMapView();
        if (v == null) {
            return;
        }
        Vector at = ev.getClickedPosition();              // from the middle of the frame; the map top is north
        int s = v.getScale().getValue();
        score(X).getScore(p.getName()).setScore(block(pixel(at.getX()), v.getCenterX(), s));
        score(Z).getScore(p.getName()).setScore(block(pixel(at.getZ()), v.getCenterZ(), s));
        score(CLICK).getScore(p.getName()).setScore(1);
    }
}
