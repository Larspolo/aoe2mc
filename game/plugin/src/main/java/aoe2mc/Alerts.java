package aoe2mc;

import java.util.function.Function;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Player;
import org.bukkit.plugin.java.JavaPlugin;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The attack alerts of the game program (#1231): when an enemy hits a unit or a building of a team, the online players
 * of that team hear a sound and see "Your units are under attack at X Z" (AlertRule: one alert per place). The town
 * bell for buildings, a goat horn for units: vanilla sounds. The server log gets each alert too (tests/test_alerts.py).
 */
final class Alerts {
    static final String BELL = "minecraft:block.bell.use";
    static final String HORN = "minecraft:item.goat_horn.sound.0";
    private final AlertRule rule = new AlertRule();
    private final JavaPlugin plugin;
    private final Function<Entity, String> side;                           // the team of an entity (AoePlugin.side)

    Alerts(JavaPlugin plugin, Function<Entity, String> side) {
        this.plugin = plugin;
        this.side = side;
    }

    /** A hit on the unit or building victim by from: an alert for the team of the victim when it is due. */
    void hit(Entity victim, boolean building, Entity from) {
        String team = side.apply(victim);
        Location at = victim.getLocation();
        if (team == null || from == null || AoePlugin.allied(team, side.apply(from))
                || !rule.due(team, building ? "buildings" : "units", at.getX(), at.getZ(), Bukkit.getCurrentTick())) {
            return;                                    // Gaia and animals have no team: no alert
        }
        String text = "Your " + (building ? "buildings" : "units") + " are under attack at " + at.getBlockX() + " "
                + at.getBlockZ();
        plugin.getLogger().info("Alert " + team + ": " + text);
        for (Player p : Bukkit.getOnlinePlayers()) {
            if (team.equals(side.apply(p))) {
                p.sendMessage(Component.text(text, NamedTextColor.RED));
                p.playSound(p.getLocation(), building ? BELL : HORN, 1.0f, 1.0f);
            }
        }
    }
}
