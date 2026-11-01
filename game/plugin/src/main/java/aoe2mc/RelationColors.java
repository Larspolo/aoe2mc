package aoe2mc;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Player;
import org.bukkit.scoreboard.Criteria;
import org.bukkit.scoreboard.DisplaySlot;
import org.bukkit.scoreboard.Objective;
import org.bukkit.scoreboard.Score;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;

import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The relation colors of one player (#5510, AoE2 DE "Unique Player Colors" off: game/relation_colors.py):
 * aoe teamcolors <player> pN=color ... | off. Vanilla sends one color per team to all clients, so the player gets a
 * mirror of the main scoreboard (Player.setScoreboard): the same teams, entries and options, with the given colors,
 * and the objectives of the display slots. The server logic keeps the main scoreboard; tick() copies it each second.
 * The sidebar of the own team color goes to the plain sidebar of the mirror (its own team has another color there).
 */
final class RelationColors {

    private final Map<UUID, Map<String, NamedTextColor>> colors = new HashMap<>();
    private final Map<UUID, Scoreboard> boards = new HashMap<>();

    boolean command(CommandSender sender, String[] args) {
        Player p = Bukkit.getPlayerExact(args[1]);
        if (p == null) {
            sender.sendMessage("No player: " + args[1]);
            return true;
        }
        Scoreboard main = Bukkit.getScoreboardManager().getMainScoreboard();
        if (args.length == 3 && args[2].equals("off")) {
            colors.remove(p.getUniqueId());
            boards.remove(p.getUniqueId());
            p.setScoreboard(main);
            sender.sendMessage("Team colors: off");
            return true;
        }
        Map<String, NamedTextColor> c = new HashMap<>();
        for (int i = 2; i < args.length; i++) {
            String[] kv = args[i].split("=", 2);
            NamedTextColor color = kv.length == 2 ? NamedTextColor.NAMES.value(kv[1]) : null;
            if (color == null) {
                sender.sendMessage("Bad color: " + args[i]);
                return true;
            }
            c.put(kv[0], color);
        }
        colors.put(p.getUniqueId(), c);
        Scoreboard b = boards.computeIfAbsent(p.getUniqueId(), u -> Bukkit.getScoreboardManager().getNewScoreboard());
        mirror(main, b, c, main.getEntryTeam(p.getName()));
        p.setScoreboard(b);
        sender.sendMessage("Team colors: " + c);
        return true;
    }

    void tick() {
        if (colors.isEmpty()) {
            return;
        }
        Scoreboard main = Bukkit.getScoreboardManager().getMainScoreboard();
        for (var it = colors.entrySet().iterator(); it.hasNext(); ) {
            var e = it.next();
            Player p = Bukkit.getPlayer(e.getKey());
            if (p == null) {                                             // a player that left: the switch stays off
                boards.remove(e.getKey());
                it.remove();
                continue;
            }
            Scoreboard b = boards.get(e.getKey());
            mirror(main, b, e.getValue(), main.getEntryTeam(p.getName()));
            if (p.getScoreboard() != b) {
                p.setScoreboard(b);
            }
        }
    }

    @SuppressWarnings("deprecation")
    private static void mirror(Scoreboard main, Scoreboard b, Map<String, NamedTextColor> colors, Team own) {
        Set<String> names = new HashSet<>();
        for (Team t : main.getTeams()) {
            names.add(t.getName());
            Team m = b.getTeam(t.getName());
            if (m == null) {
                m = b.registerNewTeam(t.getName());
            }
            m.displayName(t.displayName());
            m.prefix(t.prefix());
            m.suffix(t.suffix());
            NamedTextColor c = colors.get(t.getName());
            if (c != null) {
                m.color(c);
            } else if (t.hasColor()) {
                m.color(NamedTextColor.nearestTo(t.color()));
            }
            m.setAllowFriendlyFire(t.allowFriendlyFire());
            m.setCanSeeFriendlyInvisibles(t.canSeeFriendlyInvisibles());
            for (Team.Option o : Team.Option.values()) {
                m.setOption(o, t.getOption(o));
            }
            Set<String> entries = t.getEntries();
            for (String x : m.getEntries()) {
                if (!entries.contains(x)) {
                    m.removeEntry(x);
                }
            }
            for (String x : entries) {
                if (!m.hasEntry(x)) {
                    m.addEntry(x);
                }
            }
        }
        for (Team m : b.getTeams()) {
            if (!names.contains(m.getName())) {
                m.unregister();
            }
        }
        Map<DisplaySlot, Objective> slots = new HashMap<>();
        for (DisplaySlot s : DisplaySlot.values()) {
            Objective o = main.getObjective(s);
            if (o != null && !s.name().startsWith("SIDEBAR_TEAM_")) {
                slots.put(s, o);
            }
        }
        if (own != null && own.hasColor()) {                             // the resources of the own team (#1309)
            for (DisplaySlot s : DisplaySlot.values()) {
                if (s.name().equals("SIDEBAR_TEAM_" + NamedTextColor.NAMES.key(NamedTextColor.nearestTo(own.color())).toUpperCase(java.util.Locale.ROOT)) && main.getObjective(s) != null) {
                    slots.put(DisplaySlot.SIDEBAR, main.getObjective(s));
                }
            }
        }
        Set<String> shown = new HashSet<>();
        for (var e : slots.entrySet()) {
            Objective o = e.getValue();
            shown.add(o.getName());
            Objective m = b.getObjective(o.getName());
            if (m == null) {
                m = b.registerNewObjective(o.getName(), Criteria.DUMMY, o.displayName(), o.getRenderType());
            }
            m.displayName(o.displayName());
            if (m.getDisplaySlot() != e.getKey()) {
                m.setDisplaySlot(e.getKey());
            }
            Set<String> set = new HashSet<>();
            for (String x : main.getEntries()) {
                Score s = o.getScore(x);
                if (s.isScoreSet()) {
                    set.add(x);
                    if (m.getScore(x).getScore() != s.getScore() || !m.getScore(x).isScoreSet()) {
                        m.getScore(x).setScore(s.getScore());
                    }
                }
            }
            for (String x : b.getEntries()) {
                if (!set.contains(x) && m.getScore(x).isScoreSet()) {
                    m.getScore(x).resetScore();
                }
            }
        }
        for (Objective m : b.getObjectives()) {
            if (!shown.contains(m.getName())) {
                m.unregister();
            }
        }
    }
}
