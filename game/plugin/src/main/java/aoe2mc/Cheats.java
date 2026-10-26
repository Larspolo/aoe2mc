package aoe2mc;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;

import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerCommandPreprocessEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scoreboard.Criteria;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Scoreboard;

import io.papermc.paper.event.player.AsyncChatEvent;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.serializer.plain.PlainTextComponentSerializer;

/**
 * The AoE2 cheat codes in the chat (#816, game/cheats.py). Vanilla has no event for a chat text, so the plugin catches
 * it. "aoe cheats CODE,CODE,..." (URL-encoded) turns the cheats on with these codes; "aoe cheats -" turns them off.
 * A chat text that is a code (case and spaces at the ends do not count), also with a leading "/", does not go to
 * the chat: it sets the score aoe_cheat of the player to the number of the code (1 = the first code), and the
 * program reads it. With cheats off, the plugin knows no code, so the text is a normal chat message.
 */
final class Cheats implements Listener {
    private final JavaPlugin plugin;
    private final Map<String, Integer> codes = new HashMap<>();

    Cheats(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    boolean command(CommandSender sender, String[] args) {
        codes.clear();
        if (!args[1].equals("-")) {
            for (String c : args[1].split(",")) {
                codes.put(norm(URLDecoder.decode(c, StandardCharsets.UTF_8)), codes.size() + 1);
            }
        }
        sender.sendMessage("Cheats: " + codes.size() + " codes");
        return true;
    }

    private static String norm(String text) {
        return text.strip().toLowerCase(Locale.ROOT);
    }

    private static Objective score() {
        Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
        Objective o = sb.getObjective("aoe_cheat");
        return o != null ? o : sb.registerNewObjective("aoe_cheat", Criteria.DUMMY, Component.text("Cheat"));
    }

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onChat(AsyncChatEvent ev) {
        Integer n = codes.get(norm(PlainTextComponentSerializer.plainText().serialize(ev.message())));
        if (n != null) {
            ev.setCancelled(true);
            Player p = ev.getPlayer();
            Bukkit.getScheduler().runTask(plugin, () -> score().getScore(p.getName()).setScore(n));   // main thread
        }
    }

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onCommand(PlayerCommandPreprocessEvent ev) {
        Integer n = codes.get(norm(ev.getMessage().substring(1)));     // "/robin hood": the Minecraft command way
        if (n != null) {
            ev.setCancelled(true);
            score().getScore(ev.getPlayer().getName()).setScore(n);
        }
    }
}
