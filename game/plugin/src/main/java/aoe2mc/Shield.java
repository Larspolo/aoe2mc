package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Mob;
import org.bukkit.entity.Projectile;

/**
 * aoe shield &lt;selector&gt; &lt;part&gt; &lt;takes&gt;: the unit shields the units behind it (the Hussite Wagon, #4507,
 * game/combat.py shield_command): an enemy projectile that hits it on its way to another target deals part of its
 * damage to that target, and the unit takes "takes" hit points.
 */
public final class Shield implements Ability {
    private record Cover(double part, int takes) {}

    private final Map<UUID, Cover> shields = new HashMap<>();

    @Override
    public String name() {
        return "shield";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 4) {
            return false;
        }
        double part;
        int takes;
        try {
            part = Double.parseDouble(args[2]);
            takes = Integer.parseInt(args[3]);
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            for (Entity t : new Entity[] {AoePlugin.crew(e), e.getVehicle()}) {   // the crew of a cart, the horse of a rider
                if (t != null) {
                    shields.put(t.getUniqueId(), new Cover(part, takes));
                }
            }
            n++;
        }
        sender.sendMessage("Shield: " + n + " units");
        return true;
    }

    @Override
    public boolean shot(AoePlugin p, Projectile shot, Entity from, Entity hit, LivingEntity hurt, AoePlugin.Stats a) {
        Cover c = shields.getOrDefault(hit.getUniqueId(), shields.get(hurt.getUniqueId()));
        if (c == null || !(from instanceof Mob m) || AoePlugin.sameTeam(from, hurt)
                || !(p.body(AoePlugin.target(m)) instanceof LivingEntity aim) || aim == hurt || !aim.isValid()
                || aim.isDead() || !p.stats.containsKey(aim.getUniqueId()) || p.buildings.containsKey(aim.getUniqueId())
                || from.getLocation().distanceSquared(hurt.getLocation()) >= from.getLocation().distanceSquared(aim.getLocation())) {
            return false;
        }
        shot.remove();                         // the shot passes on to the target of the shooter
        hurt.playHurtAnimation(0);
        hurt.setHealth(Math.max(0, hurt.getHealth() - c.takes()));   // no armor (AoE2 DE wiki)
        p.nameLine(hurt);
        p.harm(aim, p.stats.get(aim.getUniqueId()), AoePlugin.volley(shot, a), from, c.part());
        return true;
    }
}
