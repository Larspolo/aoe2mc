package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;

/**
 * aoe lowhp &lt;selector&gt; &lt;hp&gt; &lt;melee&gt; &lt;pierce&gt; &lt;speed&gt;: the unit switches to another form below hp hit points
 * (the Jian Swordsman, #4472, game/combat.py low_hp_command): that melee and pierce armor and a movement speed factor;
 * at hp or more again the armor of its last aoe stats and no speed modifier.
 */
public final class LowHp implements Ability {
    private static final NamespacedKey SPEED = new NamespacedKey("aoe2mc", "low_hp_speed");

    // Below "hp" the armor "melee" and "pierce" and the speed factor "speed". low: the unit is in that form; normal:
    // the melee and pierce armor of its last aoe stats.
    private static final class Form {
        final double hp, speed;
        final int melee, pierce;
        boolean low;
        int[] normal;

        Form(double hp, int melee, int pierce, double speed) {
            this.hp = hp;
            this.melee = melee;
            this.pierce = pierce;
            this.speed = speed;
        }
    }

    private final Map<UUID, Form> forms = new HashMap<>();

    @Override
    public String name() {
        return "lowhp";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 6) {
            return false;
        }
        double hp, speed;
        int melee, pierce;
        try {
            hp = Double.parseDouble(args[2]);
            melee = Integer.parseInt(args[3]);
            pierce = Integer.parseInt(args[4]);
            speed = Double.parseDouble(args[5]);
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            forms.put(e.getUniqueId(), new Form(hp, melee, pierce, speed));
            n++;
        }
        sender.sendMessage("Low HP: " + n + " units");
        return true;
    }

    // Each tick, not at each change of the hit points: hits, heals and setHealth have many places (harm, regen, monks).
    @Override
    public void tick(AoePlugin p) {
        forms.entrySet().removeIf(en -> {
            if (!(Bukkit.getEntity(en.getKey()) instanceof LivingEntity le) || !le.isValid()) {
                return true;
            }
            Form l = en.getValue();
            AoePlugin.Stats s = p.stats.get(en.getKey());
            if (s == null) {
                return false;
            }
            if (l.low && (s.melee() != l.melee || s.pierce() != l.pierce)) {
                l.low = false;                               // a new aoe stats (an upgrade) set the normal armor
            }
            boolean low = le.getHealth() < l.hp;
            if (low == l.low) {
                return false;
            }
            if (low) {
                l.normal = new int[] {s.melee(), s.pierce()};
            }
            int m = low ? l.melee : l.normal[0], pi = low ? l.pierce : l.normal[1];
            p.stats.put(en.getKey(), new AoePlugin.Stats(s.attack(), m, pi, s.ranged(), s.pierces(), s.classes(),
                    s.bonus(), s.reload(), s.taken(), s.friendly(), s.less(), s.ignores(), s.rage(), s.reflect()));
            AttributeInstance speed = le.getAttribute(Attribute.MOVEMENT_SPEED);
            if (speed != null) {
                speed.removeModifier(SPEED);
                if (low) {
                    speed.addTransientModifier(new AttributeModifier(SPEED, l.speed - 1,
                            AttributeModifier.Operation.MULTIPLY_SCALAR_1));
                }
            }
            l.low = low;
            return false;
        });
    }
}
