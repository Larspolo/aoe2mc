package aoe2mc;

import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Projectile;

/**
 * A unit ability of the plugin (#4589, epic #4387): its command "aoe NAME ..." and the hooks of the fights that it
 * uses. A new ability is one new class and one line in src/main/resources/META-INF/services/aoe2mc.Ability
 * (ServiceLoader, merge=union): no change of AoePlugin, so parallel ability PRs do not conflict there. AoePlugin calls
 * each hook of each ability once; the default methods do nothing. The class needs a public constructor with no
 * arguments (ServiceLoader).
 */
public interface Ability {
    /** The first argument of its command (aoe NAME ...). */
    String name();

    /** The command aoe NAME args[1] ...: false when the number of arguments does not fit (an unknown command). */
    boolean command(AoePlugin p, CommandSender sender, String[] args);

    /** Each server tick. */
    default void tick(AoePlugin p) {
    }

    /** The ticks between two melee hits of unit, from the reload of its aoe stats (the Temple Guard, #4468). */
    default int reload(Entity unit, int reload) {
        return reload;
    }

    /** A melee hit of unit: its reload starts. */
    default void struck(Entity unit) {
    }

    /** The attack more of a hit of unit e (the Jaguar Warrior, #4467). */
    default int attack(Entity e) {
        return 0;
    }

    /** Unit by killed a unit with AoE2 values. */
    default void killed(Entity by) {
    }

    /** An enemy projectile of from with the values a hits entity hit (hurt: the entity with its hit points, the horse
     *  of a rider). True: the ability took the hit (the shot does nothing more, the Hussite Wagon, #4507). */
    default boolean shot(AoePlugin p, Projectile shot, Entity from, Entity hit, LivingEntity hurt, AoePlugin.Stats a) {
        return false;
    }

    /** After a melee hit of from with the values a on hurt (target: the entity that the hit was on, the rider of a
     *  horse; the elephants, #4397). */
    default void melee(AoePlugin p, Entity from, AoePlugin.Stats a, Entity hurt, Entity target) {
    }
}
