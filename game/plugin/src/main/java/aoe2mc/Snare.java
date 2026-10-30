package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;

/**
 * aoe snare &lt;selector&gt; &lt;ticks&gt; &lt;attack&gt; &lt;amplifier&gt; &lt;effect ticks&gt;: the charged shot (the Bolas Rider,
 * #4548, game/combat.py snare_command). The first projectile hit on a unit after ticks has attack more and gives the
 * target the vanilla effect slowness of amplifier (15 % for each level, the AoE2 value) for effect ticks, then the
 * charge starts again; a new unit starts full.
 */
public final class Snare implements Ability {
    private final Map<UUID, int[]> snares = new HashMap<>();   // {ticks, attack, amplifier, effect ticks}
    private final Map<UUID, Integer> snared = new HashMap<>(); // the first tick of the next charged shot

    @Override
    public String name() {
        return "snare";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 6) {
            return false;
        }
        int[] c = new int[4];
        try {
            for (int i = 0; i < 4; i++) {
                c[i] = Integer.parseInt(args[i + 2]);
            }
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad value: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            snares.put(e.getUniqueId(), c);
            if (AoePlugin.crew(e) instanceof Entity r) {
                snares.put(r.getUniqueId(), c);                    // the rider of a mounted unit shoots (#710)
            }
            n++;
        }
        sender.sendMessage("Snare: " + n + " units");
        return true;
    }

    @Override
    public AoePlugin.Stats hit(AoePlugin p, Entity from, LivingEntity hurt, AoePlugin.Stats a) {
        int[] c = snares.get(from.getUniqueId());
        int now = Bukkit.getCurrentTick();
        if (c == null || now < snared.getOrDefault(from.getUniqueId(), 0)) {
            return a;
        }
        snared.put(from.getUniqueId(), now + c[0]);
        hurt.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, c[3], c[2]));
        return new AoePlugin.Stats(a.attack() + c[1], a.melee(), a.pierce(), a.ranged(), a.pierces(), a.classes(),
                a.bonus(), a.reload(), a.taken(), a.friendly(), a.less(), a.ignores(), a.rage(), a.reflect());
    }
}
