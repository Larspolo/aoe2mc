package aoe2mc;

import net.kyori.adventure.text.Component;
import org.bukkit.Bukkit;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.scoreboard.Team;

import io.papermc.paper.event.player.AsyncChatEvent;

/**
 * The name of a normal chat line in the color of its team pN, the AoE2 player color (#3681). Vanilla colors it with
 * the team, but Paper keeps the display name of the login, before game/run.py puts the player on a team. The line
 * stays "<name> text" (the join regex of game/run.py). A player with no team or no team color keeps the default.
 */
final class ChatName implements Listener {

    @EventHandler(priority = EventPriority.NORMAL, ignoreCancelled = true)
    public void onChat(AsyncChatEvent ev) {
        Team team = Bukkit.getScoreboardManager().getMainScoreboard().getEntryTeam(ev.getPlayer().getName());
        if (team == null || !team.hasColor()) {
            return;
        }
        Component name = Component.text(ev.getPlayer().getName(), team.color());
        ev.renderer((source, display, message, viewer) -> Component.translatable("chat.type.text", name, message));
    }
}
