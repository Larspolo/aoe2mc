package aoe2mc;

import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.NamespacedKey;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeInstance;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Mob;

/**
 * aoe aura &lt;selector&gt; &lt;blocks&gt; &lt;speed&gt; &lt;attack speed&gt; &lt;tag&gt;,...: the own units with one of the
 * tags (their type tags aoe2mc.t&lt;ID&gt;) within blocks of the unit move and attack faster (the Centurion, #4470,
 * game/abilities/aura.py): movement speed * (1 + speed), melee reload / (1 + attack speed). Two auras do not add up: the highest values count (AoE2 wiki "Centurion": no stack,
 * not for allies).
 */
public final class Aura implements Ability {
    private record Spec(double blocks, double speed, double attack, Set<String> tags) {}

    // one key for all auras: a second aura replaces the modifier, so two auras do not stack (the Minecraft feature)
    private static final NamespacedKey KEY = new NamespacedKey("aoe2mc", "aura");
    private final Map<UUID, Spec> auras = new HashMap<>();
    private Map<UUID, Double> boosted = new HashMap<>();   // the attack speed of each unit in an aura now

    @Override
    public String name() {
        return "aura";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 6) {
            return false;
        }
        double blocks, speed, attack;
        try {
            blocks = Double.parseDouble(args[2]);
            speed = Double.parseDouble(args[3]);
            attack = Double.parseDouble(args[4]);
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            auras.put(e.getUniqueId(), new Spec(blocks, speed, attack, Set.copyOf(List.of(args[5].split(",")))));
            n++;
        }
        sender.sendMessage("Aura: " + n + " units");
        return true;
    }

    // Each second: the own units with a tag of a live aura in its circle get its boost, the others lose it.
    @Override
    public void tick(AoePlugin p) {
        if (Bukkit.getCurrentTick() % 20 != 0) {
            return;
        }
        auras.keySet().removeIf(id -> Bukkit.getEntity(id) == null || !Bukkit.getEntity(id).isValid());
        Map<UUID, double[]> now = new HashMap<>();
        for (var a : auras.entrySet()) {
            Entity c = Bukkit.getEntity(a.getKey());
            Spec u = a.getValue();
            String side = AoePlugin.side(c);
            for (Entity t : c.getNearbyEntities(u.blocks, u.blocks, u.blocks)) {
                if (t instanceof Mob && side != null && side.equals(AoePlugin.side(t)) && !Collections.disjoint(t.getScoreboardTags(), u.tags)
                        && t.getLocation().distanceSquared(c.getLocation()) <= u.blocks * u.blocks) {
                    now.merge(t.getUniqueId(), new double[] {u.speed, u.attack},
                            (x, y) -> new double[] {Math.max(x[0], y[0]), Math.max(x[1], y[1])});
                }
            }
        }
        for (UUID id : boosted.keySet()) {
            if (!now.containsKey(id) && Bukkit.getEntity(id) instanceof Mob mob
                    && mob.getAttribute(Attribute.MOVEMENT_SPEED) instanceof AttributeInstance attr) {
                attr.removeModifier(KEY);
            }
        }
        Map<UUID, Double> next = new HashMap<>();
        for (var e : now.entrySet()) {
            if (Bukkit.getEntity(e.getKey()) instanceof Mob mob
                    && mob.getAttribute(Attribute.MOVEMENT_SPEED) instanceof AttributeInstance attr) {
                AttributeModifier m = attr.getModifier(KEY);
                if (m == null || m.getAmount() != e.getValue()[0]) {
                    attr.removeModifier(KEY);
                    attr.addTransientModifier(new AttributeModifier(KEY, e.getValue()[0],
                            AttributeModifier.Operation.ADD_SCALAR));
                }
                next.put(e.getKey(), e.getValue()[1]);
            }
        }
        boosted = next;
    }

    @Override
    public int reload(Entity unit, int reload) {
        return (int) Math.round(reload / (1 + boosted.getOrDefault(unit.getUniqueId(), 0.0)));
    }
}
