package aoe2mc;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.scoreboard.Team;

import io.papermc.paper.event.player.AsyncChatEvent;

/**
 * The chat of the spectators (#3554, team spec of game/run.py SPECTATORS). A chat line of a spectator reaches the
 * spectators only, as in AoE2 DE: a player must not hear where the enemy is. The console keeps the line (the logs).
 * Vanilla has no rule for the receivers of a chat line, so the plugin removes the players of the other teams.
 */
final class SpecChat implements Listener {

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onChat(AsyncChatEvent ev) {
        Team spec = Bukkit.getScoreboardManager().getMainScoreboard().getTeam("spec");
        if (spec == null || !spec.hasEntry(ev.getPlayer().getName())) {
            return;
        }
        ev.viewers().removeIf(v -> v instanceof Player p && !spec.hasEntry(p.getName()));
    }
}
