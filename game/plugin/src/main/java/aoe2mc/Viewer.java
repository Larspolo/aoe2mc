package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.GameMode;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerGameModeChangeEvent;
import org.bukkit.event.player.PlayerToggleSneakEvent;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * The game mode switch of a viewer of the live replay (#910, owner decision #782). The replay gives each player the
 * tag aoe_viewer (replay.VIEWER, #737). A viewer in adventure mode can fly, and has the hotbar items of the replay
 * control. A double tap of the sneak key (two presses within TAP ms) changes between spectator mode and adventure
 * mode: a spectator's clicks do not reach the server, its keys do (PlayerToggleSneakEvent). One tap stays "fly down".
 * Vanilla has no command for "may fly", so the plugin sets it. The game program does not add the tag.
 */
final class Viewer implements Listener {
    static final String TAG = "aoe_viewer";
    static final long TAP = 400;                          // ms between the two presses of a double tap
    static final long LATER = 20;                         // ticks: the replay adds the tag after its gamemode command
    private final JavaPlugin plugin;
    private final Map<UUID, Long> pressed = new HashMap<>();

    Viewer(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    @EventHandler(ignoreCancelled = true)
    public void onSneak(PlayerToggleSneakEvent ev) {
        Player p = ev.getPlayer();
        if (!ev.isSneaking() || !p.getScoreboardTags().contains(TAG)) {
            return;
        }
        long now = System.currentTimeMillis();
        Long last = pressed.put(p.getUniqueId(), now);
        if (last == null || now - last > TAP) {
            return;
        }
        pressed.remove(p.getUniqueId());                  // a third press starts a new double tap
        if (p.getGameMode() == GameMode.SPECTATOR) {
            p.setGameMode(GameMode.ADVENTURE);
            fly(p);
        } else if (p.getGameMode() == GameMode.ADVENTURE) {
            p.setGameMode(GameMode.SPECTATOR);
        }
    }

    @EventHandler(ignoreCancelled = true)
    public void onMode(PlayerGameModeChangeEvent ev) {    // also the "gamemode adventure" of the replay start (#737)
        if (ev.getNewGameMode() != GameMode.ADVENTURE) {
            return;
        }
        Player p = ev.getPlayer();                        // the change resets the flight after the event: set it later
        Bukkit.getScheduler().runTaskLater(plugin, () -> {
            if (p.isOnline() && p.getGameMode() == GameMode.ADVENTURE && p.getScoreboardTags().contains(TAG)
                    && !p.getAllowFlight()) {
                fly(p);
            }
        }, LATER);
    }

    private static void fly(Player p) {
        p.setAllowFlight(true);
        p.setFlying(true);
    }
}
