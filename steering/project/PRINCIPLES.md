# Principles: the project

The direction of aoe2mc: what the owner prefers when two good options compete, for the project (what aoe2mc becomes). The agent made this file from the owner's decisions until 2026-10-27 (decision tickets, owner comments, `/human` sessions). Each principle names the decisions that it comes from. `steering/project/DECISIONS.md` is the log of these decisions. The system principles are in `steering/system/PRINCIPLES.md`. The numbers P1 to P12 are the same in both files.

How to use it:
- **Agents.** Before you recommend an option (decision ticket, PR, epic), compare each option with these principles.
  Recommend the option that follows them, and name the principle in the recommendation ("follows P3").
  When two principles conflict, say so in the ticket: that is a real decision for the owner.
- **Owner.** When your answer does not follow a principle, the agent tells you in the comment that records the
  decision. Then you can change the principle, or keep your answer as an exception. Edit this file at any time:
  the agents follow the version on `main`.
- **Over time.** Each decision adds a line to `steering/project/DECISIONS.md`. The `improve` skill measures how often the owner
  takes the recommendation and updates the principles when they do not predict the owner's answers.

## P1. AoE2 sets the rules, Minecraft sets the form

Game behavior, numbers, cheat codes, tooltips and replay events follow AoE2 exactly. The look, the controls and the
mob types follow what a Minecraft player expects.
- Big cats are wolves, because a Minecraft player does not expect a hostile cat (#43).
- The cheat codes, tooltips and garrison work as in AoE2 (#816, #965, #807). Units walk under a town center, and a
  ship unloads at the shore, as in AoE2 (#718, #1492).
- The selection feels like Minecraft: hold right click (#992). A gate is bars that rise (#1327).
- Siege units are mobs in minecarts, and they must not overlap: "similar behaviour between AoE and MC" (#1525).

## P2. Minecraft features first

Use a feature of Minecraft (mob AI, path finding, teams, scoreboards, attributes, block states, datapacks) before you
write own logic. The game program can use a Paper plugin when vanilla has no command for the job (#431, owner rule
2026-10-26; CLAUDE.md, "Rules of the domain"). Horses get one scale, not own path logic (#1096).

## P3. The default is vanilla and clean. Extras are opt-in

A converted world loads in vanilla Minecraft with no warning. A feature that needs more (an experimental warning,
a Paper server, a fee, a heavy effect) is an option, not the default.
- Custom biomes are an option; switch the default when the warning goes away (#219).
- Fog only with `--ambience full` or `--fog` (#1625). Installers stay unsigned, with no fee (#1544).
- Hold right click needs Paper; vanilla keeps two clicks (#992).

## P4. Ship "fine for now", expand later

This principle is in `steering/system/PRINCIPLES.md`. It also applies to the project: take the smallest option that works now, and make the next step a later ticket.

## P8. Few buttons, and each action is also a command

Hotbar slots are scarce: put actions behind one item or a chest menu, and give each action a command too
(#686, #1232, #1314, #1106). The building menus are a Paper chest menu (#618).

## P9. The player always sees what happens

Show clear feedback: a larger mark on the target, a visible selection border, a ghost building, hints in the action
bar, damage stages that look different from construction (#823, #988, #793, #797, #1332). An action that surprises
the player is a bug ("this is not nice", #989).

## P12. Before a release, the play test first

Until the next release, the agents make the game ready for a play test and improve what the player sees and does.
New features of milestone C and extras wait with the label `after-release` (owner, 2026-11-01; #4175, #5120, #5378;
the full rule: `steering/project/RELEASE.md`, "Release focus"). A ticket outside the focus is not urgent work: hold it.

## Tensions

- P1 against P8: AoE2 has many buttons, Minecraft has 9 hotbar slots. Up to now P8 won: group the AoE2 buttons (#1314).
