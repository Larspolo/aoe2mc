package aoe2mc;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
    private static final Pattern TAUNT = Pattern.compile("^\\s*0*([1-9]\\d{0,2})(\\s|$)");   // "11", "11 haha"
    private static final Pattern GIVE = Pattern.compile("give\\s+\\S+\\s+(?:aoe:)?(\\w+)(\\s+\\d+)?");
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
        String text = PlainTextComponentSerializer.plainText().serialize(ev.message());
        Integer n = codes.get(norm(text));
        Player p = ev.getPlayer();
        if (n != null) {
            ev.setCancelled(true);
            Bukkit.getScheduler().runTask(plugin, () -> score().getScore(p.getName()).setScore(n));   // main thread
            return;
        }
        Matcher m = TAUNT.matcher(text);
        if (m.find()) {                       // a taunt (#3318): the chat stays, the program shows the text and plays the sound
            int t = Integer.parseInt(m.group(1));
            Bukkit.getScheduler().runTask(plugin, () -> {
                Scoreboard sb = Bukkit.getScoreboardManager().getMainScoreboard();
                Objective o = sb.getObjective("aoe_taunt");
                if (o != null) {
                    o.getScore(p.getName()).setScore(t);
                }
            });
        }
    }

    @EventHandler(priority = EventPriority.LOWEST, ignoreCancelled = true)
    public void onCommand(PlayerCommandPreprocessEvent ev) {
        String text = norm(ev.getMessage().substring(1));
        Matcher g = GIVE.matcher(text);                               // "/give @s gold 100" -> the code "give gold" (#5153)
        Integer n = codes.get(g.matches() ? "give " + g.group(1) : text);     // "/robin hood": the Minecraft command way
        if (n != null) {
            ev.setCancelled(true);
            score().getScore(ev.getPlayer().getName()).setScore(n);
        }
    }
}
