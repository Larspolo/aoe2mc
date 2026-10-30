package aoe2mc;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

import org.bukkit.Bukkit;
import org.bukkit.entity.Entity;

/**
 * AoE2 damage over time (#4339): the key "damage_over_time" of game/data/train.jsonl (Curare: poison, Red Cliffs
 * Tactics: fire). "aoe stats" gives a unit its rule. Each hit of that unit on a target of the rule classes starts one
 * damage over time: the target loses the damage in equal parts over the ticks, with no armor. Two hits add up, as in
 * AoE2. Not the vanilla poison effect: it stops at 1 health, it has a fixed rate and it does not hurt a building target
 * (the score aoe_hp). A frozen server (pause, /tick freeze) stops it; the tick rate (the game speed) changes it.
 */
final class Dot {
    /** damage: the AoE2 damage of one hit, ticks: its time, classes: the target classes (empty: each unit). */
    record Rule(double damage, int ticks, Set<String> classes) {}

    /** What one step of a damage over time does to its target (AoePlugin): damage to a unit, whole (the whole hit
     *  points since the last step) to a building target, which has whole hit points. */
    interface Hurt {
        void apply(Entity target, UUID from, double damage, int whole);
    }

    private static final class Active {
        final UUID target, from;
        final Rule rule;
        int ticks;
        double dealt;

        Active(UUID target, UUID from, Rule rule) {
            this.target = target;
            this.from = from;
            this.rule = rule;
        }
    }

    static final int STEP = 10;                             // ticks between two parts of the damage

    private final Map<UUID, Rule> rules = new HashMap<>();
    private final List<Active> active = new ArrayList<>();

    /** The rule of a unit (null: none). */
    void set(UUID unit, Rule rule) {
        if (rule == null) {
            rules.remove(unit);
        } else {
            rules.put(unit, rule);
        }
    }

    /** A hit of from on target with these classes: a damage over time starts when the rule of from has a class of them. */
    void start(Entity from, Entity target, Set<String> classes) {
        Rule r = from == null ? null : rules.get(from.getUniqueId());
        if (r != null && target != null && (r.classes().isEmpty() || !Collections.disjoint(r.classes(), classes))) {
            active.add(new Active(target.getUniqueId(), from.getUniqueId(), r));
        }
    }

    /** Each STEP ticks: the part of each damage over time since the last step. A dead target and an end remove it. */
    void tick(Hurt hurt) {
        if (Bukkit.getServerTickManager().isFrozen()) {
            return;
        }
        for (Iterator<Active> it = active.iterator(); it.hasNext(); ) {
            Active a = it.next();
            a.ticks = Math.min(a.rule.ticks(), a.ticks + STEP);
            double total = a.rule.damage() * a.ticks / a.rule.ticks(), part = total - a.dealt;
            int whole = (int) (Math.floor(total) - Math.floor(a.dealt));
            a.dealt = total;
            Entity t = Bukkit.getEntity(a.target);
            if (t == null || !t.isValid()) {
                it.remove();
                continue;
            }
            if (part > 0) {
                hurt.apply(t, a.from, part, whole);
            }
            if (a.ticks >= a.rule.ticks()) {
                it.remove();
            }
        }
    }
}
