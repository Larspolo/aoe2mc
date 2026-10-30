package aoe2mc;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

import org.bukkit.command.CommandSender;
import org.bukkit.entity.Entity;
import org.bukkit.entity.Mob;

/**
 * aoe trample &lt;selector&gt; &lt;part&gt; &lt;blocks&gt; [&lt;damage&gt; &lt;ignore 0|1&gt;]: trample damage (the elephants, #4397,
 * game/combat.py trample_command): a melee hit of the unit also hurts each other enemy unit within blocks of the target
 * with part of the AoE2 damage on it, or with a fixed damage less its melee armor (ignore 1: no armor; a technology,
 * epic #4096). AoePlugin.trample does the hit (also the charged hit of an Urumi Swordsman, #4544).
 */
public final class Trample implements Ability {
    private final Map<UUID, AoePlugin.Blast> tramples = new HashMap<>();

    @Override
    public String name() {
        return "trample";
    }

    @Override
    public boolean command(AoePlugin p, CommandSender sender, String[] args) {
        if (args.length != 4 && args.length != 6) {
            return false;
        }
        AoePlugin.Blast tr;
        try {
            tr = new AoePlugin.Blast(Double.parseDouble(args[2]), Double.parseDouble(args[3]),
                    args.length == 6 ? Double.parseDouble(args[4]) : 0, args.length == 6 && args[5].equals("1"));
        } catch (NumberFormatException e) {
            sender.sendMessage("Bad number: " + e.getMessage());
            return true;
        }
        int n = 0;
        for (Entity e : AoePlugin.select(sender, args[1])) {
            tramples.put(e.getUniqueId(), tr);
            if (e instanceof Mob mob) {
                tramples.put(AoePlugin.crew(mob).getUniqueId(), tr);   // the crew of a siege unit hits (#836)
            }
            n++;
        }
        sender.sendMessage("Trample: " + n + " units");
        return true;
    }

    @Override
    public void melee(AoePlugin p, Entity from, AoePlugin.Stats a, Entity hurt, Entity target) {
        p.trample(from, a, hurt, target, tramples.get(from.getUniqueId()));
    }
}
