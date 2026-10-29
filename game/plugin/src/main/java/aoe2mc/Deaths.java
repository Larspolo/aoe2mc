package aoe2mc;

import java.util.ArrayList;
import java.util.List;

import org.bukkit.Bukkit;
import org.bukkit.Location;
import org.bukkit.Particle;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Display;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.entity.TextDisplay;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.plugin.java.JavaPlugin;
import org.bukkit.scoreboard.Scoreboard;
import org.bukkit.scoreboard.Team;
import org.bukkit.util.Transformation;
import org.joml.AxisAngle4f;
import org.joml.Vector3f;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;

/**
 * The death marks of the live replay (#846, game/replay.py): "aoe deathmarks on|off". With the marks on, a unit with the
 * tag aoe2mc.pop (replay.COUNTED) that dies gives soul particles and a text display "☠" in its team color at its place,
 * for SECONDS. So a spectator sees where the fights are. Vanilla has no "on death" command: the plugin listens to the
 * death event. The game program does not turn the marks on. The display is not persistent: a restart removes it.
 * A player who does not see the unit (the fog of Replay.fog: Player#hideEntity) gets no particles and no mark (#3084).
 */
final class Deaths implements Listener {
    static final String TAG = "aoe2mc.pop";
    static final String MARK = "aoe2mc.deathmark";
    static final int SECONDS = 5;
    static final float SCALE = 2.5f;                      // the default text is a quarter block: too small from afar
    private final JavaPlugin plugin;
    private boolean on;

    Deaths(JavaPlugin plugin) {
        this.plugin = plugin;
    }

    boolean command(CommandSender sender, String[] args) {
        on = args[1].equals("on");
        sender.sendMessage("Death marks: " + (on ? "on" : "off"));
        return true;
    }

    // LOW: runs before AoePlugin.onDeath, which removes the boat or the minecart of the crew (#3019)
    @EventHandler(priority = EventPriority.LOW)
    public void onDeath(EntityDeathEvent ev) {
        LivingEntity e = ev.getEntity();
        Entity vehicle = e.getVehicle();
        boolean ship = vehicle != null && vehicle.getScoreboardTags().contains(TAG);   // the crew of a ship or siege unit
        if (!on || !ship && !e.getScoreboardTags().contains(TAG)) {
            return;
        }
        Entity body = ship ? vehicle : e;
        Scoreboard board = Bukkit.getScoreboardManager().getMainScoreboard();
        Team team = board.getEntityTeam(e) != null ? board.getEntityTeam(e) : board.getEntityTeam(body);
        NamedTextColor color = team != null && team.hasColor() && team.color() instanceof NamedTextColor c ? c
                : NamedTextColor.WHITE;
        Location at = body.getLocation();
        List<Player> blind = new ArrayList<>();
        for (Player p : e.getWorld().getPlayers()) {
            if (p.canSee(body)) {
                p.spawnParticle(Particle.SOUL, at.clone().add(0, 0.5, 0), 12, 0.3, 0.4, 0.3, 0.02);
            } else {
                blind.add(p);
            }
        }
        TextDisplay mark = e.getWorld().spawn(at.clone().add(0, 1.2, 0), TextDisplay.class, d -> {
            d.text(Component.text("☠", color));
            d.setBillboard(Display.Billboard.CENTER);
            d.setTransformation(new Transformation(new Vector3f(), new AxisAngle4f(), new Vector3f(SCALE, SCALE, SCALE),
                    new AxisAngle4f()));
            d.setPersistent(false);
            d.addScoreboardTag(MARK);
            blind.forEach(p -> p.hideEntity(plugin, d));      // before the spawn packet: the fog hides the unit
        });
        Bukkit.getScheduler().runTaskLater(plugin, mark::remove, SECONDS * 20L);
    }
}
