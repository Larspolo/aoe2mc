package aoe2mc;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Function;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.command.CommandSender;
import org.bukkit.command.ProxiedCommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.scoreboard.Team;
import org.bukkit.util.Vector;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.event.ClickEvent;
import net.kyori.adventure.text.event.HoverEvent;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The attack alerts of the game program (#1231): when an enemy hits a unit or a building of a team, the online players
 * of that team hear a sound and see "Your units are under attack at X Z" (AlertRule: one alert per place). The online
 * players of the allied teams hear another horn and see "Your ally is under attack at X Z" (#1941). The town
 * bell for buildings, a goat horn for units: vanilla sounds. The server log gets each alert too (tests/test_alerts.py).
 * A click on the alert line runs "/aoego X Z" (#1816, the AoE2 key "go to last alert"): the player who clicks goes to a
 * view of the place (flying in creative, else with slow falling). The command has no permission, so a player who is no operator can use it and the client shows no
 * confirmation screen; it goes only to the last KEEP alert places of the own team.
 */
final class Alerts {
    static final String BELL = "minecraft:block.bell.use";
    static final String HORN = "minecraft:item.goat_horn.sound.0";
    static final String ALLY = "minecraft:item.goat_horn.sound.1";        // another horn: an ally is attacked (#1941)
    static final int KEEP = 10;                                            // alert places of a team for "aoego"
    static final double UP = 12, BACK = 12;                                // the view: blocks above and south of it
    static final int FALL = 200;                                           // ticks of slow falling without flight
    private final Map<String, Deque<Location>> places = new HashMap<>();    // team -> its last alert places
    private final AlertRule rule = new AlertRule();
    private final Set<String> hits = new TreeSet<>();                    // teams with an enemy hit since "aoe hits"
    private final JavaPlugin plugin;
    private final Function<Entity, String> side;                           // the team of an entity (AoePlugin.side)

    Alerts(JavaPlugin plugin, Function<Entity, String> side) {
        this.plugin = plugin;
        this.side = side;
    }

    /** A hit on the unit or building victim by from: an alert for the team of the victim and for its allies (#1941)
     * when it is due. */
    void hit(Entity victim, boolean building, Entity from) {
        String team = side.apply(victim);
        if (team == null || from == null || AoePlugin.allied(team, side.apply(from))) {
            return;                                    // Gaia and animals have no team: no alert
        }
        hits.add(team);                                // each hit, not only an alert: the battle music (#5342)
        Location at = victim.getLocation();
        long tick = Bukkit.getCurrentTick();
        String where = " under attack at " + at.getBlockX() + " " + at.getBlockZ();
        if (rule.due(team, building ? "buildings" : "units", at.getX(), at.getZ(), tick)) {
            alert(team, "Your " + (building ? "buildings" : "units") + " are" + where, at, building ? BELL : HORN);
        }
        List<String> teams = new ArrayList<>();                        // the scoreboard teams: also with no client
        for (Team t : Bukkit.getScoreboardManager().getMainScoreboard().getTeams()) {
            teams.add(t.getName());
        }
        for (String t : rule.allies(team, teams, AoePlugin::allied, at.getX(), at.getZ(), tick)) {
            alert(t, "Your ally is" + where, at, ALLY);
        }
    }

    /** "aoe hits": the teams with an enemy hit on a unit or a building since the last call (game/music.py, the battle
     * music, #5342): one answer per second for all teams. */
    String hits() {
        String out = "Hits:" + (hits.isEmpty() ? "" : " " + String.join(" ", hits));
        hits.clear();
        return out;
    }

    /** Send the alert text with the sound to the online players of the team, and keep the place for "aoego". */
    private void alert(String team, String text, Location at, String sound) {
        plugin.getLogger().info("Alert " + team + ": " + text);
        Deque<Location> last = places.computeIfAbsent(team, t -> new ArrayDeque<>());
        last.addFirst(at.clone());
        while (last.size() > KEEP) {
            last.removeLast();
        }
        Component line = Component.text(text, NamedTextColor.RED)
                .clickEvent(ClickEvent.runCommand("/aoego " + at.getBlockX() + " " + at.getBlockZ()))
                .hoverEvent(HoverEvent.showText(Component.text("Click: go there")));
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (team.equals(side.apply(p))) {
                p.sendMessage(line);
                p.playSound(p.getLocation(), sound, 1.0f, 1.0f);
            }
        }
    }

    /** "aoego X Z": the player who runs it (also through "execute as") goes UP blocks above and BACK blocks south of
     * the alert place of the own team at block X Z, in free air above the highest block, and looks at it. */
    boolean go(CommandSender sender, String[] args) {
        CommandSender who = sender instanceof ProxiedCommandSender px ? px.getCallee() : sender;
        if (!(who instanceof Player p) || args.length != 2) {
            sender.sendMessage("Usage (a player): /aoego <x> <z>");
            return true;
        }
        Location at = places.getOrDefault(side.apply(p), new ArrayDeque<>()).stream()
                .filter(l -> args[0].equals(String.valueOf(l.getBlockX())) && args[1].equals(String.valueOf(l.getBlockZ())))
                .findFirst().orElse(null);
        if (at == null) {
            p.sendMessage(Component.text("No alert of your team there", NamedTextColor.GRAY));
            return true;
        }
        Location view = view(p, at);
        plugin.getLogger().info("Go " + p.getName() + ": " + view.getBlockX() + " " + view.getBlockY() + " "
                + view.getBlockZ());
        return true;
    }

    /** Put player p UP blocks above and BACK blocks south of the place at, in free air above the highest block, and
     * let it look at the place: the view of an alert (aoego) and of the "Go to" menu (aoe view, game/goto.py, #1830).
     * In creative mode it flies there, else slow falling stops the fall damage. Returns the view. */
    static Location view(Player p, Location at) {
        Location view = at.clone().add(0, UP, BACK);
        double free = at.getWorld().getHighestBlockYAt(view.getBlockX(), view.getBlockZ()) + 1;
        view.setY(Math.max(view.getY(), free));
        view.setDirection(at.toVector().subtract(view.toVector().add(new Vector(0, p.getEyeHeight(), 0))));
        p.teleport(view);
        if (p.getAllowFlight()) {
            p.setFlying(true);                         // creative: it stays at the view
        } else {                                       // adventure (two people): it sinks slowly, with no damage
            p.addPotionEffect(new PotionEffect(PotionEffectType.SLOW_FALLING, FALL, 0, true, false));
        }
        return view;
    }
}
