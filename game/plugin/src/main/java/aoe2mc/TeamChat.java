package aoe2mc;

import java.util.Locale;

import org.bukkit.Bukkit;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerCommandPreprocessEvent;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextColor;

/**
 * The team chat to the allies (#3553), the AoE2 chat target "Allies". Vanilla /teammsg (/tm) goes only to the team
 * of the writer (pN, one AoE2 player), and vanilla has no message to several teams: so the plugin sends the line of a
 * team with an ally (aoe allies) to the persons of the own and the allied teams. A team with no ally, and a person
 * with no team, keep the vanilla command. The form is the vanilla team message form, with the team color.
 */
final class TeamChat implements Listener {

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onCommand(PlayerCommandPreprocessEvent ev) {
        String[] parts = ev.getMessage().split(" ", 2);
        String cmd = parts[0].toLowerCase(Locale.ROOT);
        if (!(cmd.equals("/teammsg") || cmd.equals("/tm")) || parts.length < 2 || parts[1].isBlank()) {
            return;
        }
        Player p = ev.getPlayer();
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Team own = sb.getEntryTeam(p.getName());
        if (own == null || sb.getTeams().stream().noneMatch(t -> t != own && AoePlugin.allied(own.getName(), t.getName()))) {
            return;
        }
        ev.setCancelled(true);
        TextColor color = own.hasColor() ? own.color() : NamedTextColor.WHITE;
        Component line = Component.text("[").append(own.displayName()).append(Component.text("] "))
                .color(color).append(Component.text("<" + p.getName() + "> " + parts[1], NamedTextColor.WHITE));
        for (Player r : Bukkit.getOnlinePlayers()) {
            Team t = sb.getEntryTeam(r.getName());
            if (t != null && AoePlugin.allied(own.getName(), t.getName())) {
                r.sendMessage(r == p ? Component.text("-> ").append(line) : line);
            }
        }
        Bukkit.getConsoleSender().sendMessage(line);   // the logs keep the line
    }
}
