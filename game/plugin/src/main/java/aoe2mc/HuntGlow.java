package aoe2mc;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.Plugin;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

import io.papermc.paper.event.player.PlayerTrackEntityEvent;

/**
 * The switch "Highlight huntable animals" of the Game menu (#5509, game/hunt_highlight.py): the animals glow only for
 * the players that turned it on. The vanilla effect glowing shows to all players, so the plugin sends the effect to the
 * client of one player only (Player#sendPotionEffectChange); the server and the other clients do not change.
 * `aoe huntglow <players> on <uuid> ...`: these animals glow for the players; `add <uuid> ...`: these too (a long
 * list, rcon.MAX); `off`: none.
 * A client forgets the effect when the entity leaves its view, so the plugin sends it again when the client tracks
 * the entity again (PlayerTrackEntityEvent, one tick later: after the spawn packet).
 */
final class HuntGlow implements Listener {
    private final Plugin plugin;
    private final Map<UUID, Set<UUID>> glows = new HashMap<>();     // player -> the animals that glow for it

    HuntGlow(Plugin plugin) {
        this.plugin = plugin;
    }

    boolean command(CommandSender sender, List<Player> players, String[] args) {
        boolean on = !args[2].equals("off");
        int n = 0;
        for (Player p : players) {
            Set<UUID> old = args[2].equals("add") ? null : glows.remove(p.getUniqueId());
            for (UUID u : old == null ? Set.<UUID>of() : old) {
                if (Bukkit.getEntity(u) instanceof LivingEntity e) {
                    p.sendPotionEffectChangeRemove(e, PotionEffectType.GLOWING);
                }
            }
            if (on) {
                Set<UUID> set = glows.computeIfAbsent(p.getUniqueId(), k -> new HashSet<>());
                for (int i = 3; i < args.length; i++) {
                    UUID u = UUID.fromString(args[i]);
                    set.add(u);
                    if (Bukkit.getEntity(u) instanceof LivingEntity e) {
                        send(p, e);
                        n++;
                    }
                }
            }
        }
        sender.sendMessage("Hunt glow: " + n + " animals, " + players.size() + " players");
        return true;
    }

    private static void send(Player p, LivingEntity e) {
        p.sendPotionEffectChange(e, new PotionEffect(PotionEffectType.GLOWING, PotionEffect.INFINITE_DURATION, 0,
                false, false));
    }

    @EventHandler
    public void onTrack(PlayerTrackEntityEvent ev) {
        Set<UUID> set = glows.get(ev.getPlayer().getUniqueId());
        Entity e = ev.getEntity();
        if (set != null && set.contains(e.getUniqueId()) && e instanceof LivingEntity le) {
            Player p = ev.getPlayer();
            Bukkit.getScheduler().runTask(plugin, () -> {
                if (p.isOnline() && le.isValid()) {
                    send(p, le);
                }
            });
        }
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent ev) {
        glows.remove(ev.getPlayer().getUniqueId());
    }
}
