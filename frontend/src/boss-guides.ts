export type BossAbilityGuide = { name: string; danger: 'tank' | 'raid' | 'position' | 'interrupt'; summary: string }
export type BossGuide = { aliases: string[]; era: 'Classic' | 'TBC'; raid: string; summary: string; health: string; healthNote: string; source: string; abilities: BossAbilityGuide[] }

// Short encounter notes are references, not judgments about individual players.
// Health and incoming damage vary across versions, raid sizes, and tuning; we only
// show a numeric value when it is explicitly tied to a source and mode.
export const BOSS_GUIDES: BossGuide[] = [
  { aliases: ['magtheridon'], era: 'TBC', raid: "Magtheridon's Lair", summary: 'Multi-phase encounter: control the Hellfire Channelers, then rotate five-person cube teams to stop Blast Nova.', health: 'Mode-specific', healthNote: 'The accessible reports may use different TBC builds; verify the source guide for the matching mode.', source: 'https://www.wowhead.com/tbc/guide/magtheridon-magtheridons-lair-strategy-burning-crusade-classic', abilities: [
    { name: 'Blast Nova', danger: 'raid', summary: 'Raid-wide fire damage over time. Five assigned players must activate their cubes together; a normal interrupt is not the mechanic.' },
    { name: 'Shadow Bolt Volley', danger: 'raid', summary: 'Channeler area damage. Spread channelers and interrupt or outrange their volleys.' },
    { name: 'Dark Mending', danger: 'interrupt', summary: 'Channeler heal that can prolong phase one; interrupt or focus the healing channeler.' },
    { name: 'Quake / Debris', danger: 'raid', summary: 'Quake interrupts casting; the 30% transition and falling debris create major raid-damage and positioning checks.' },
  ] },
  { aliases: ['gruul'], era: 'TBC', raid: "Gruul's Lair", summary: 'A growth timer increases boss damage over time while the raid manages Ground Slam, Shatter spacing, and Cave In.', health: 'Mode-specific', healthNote: 'Health differs by raid tuning; use the linked guide for the matching version.', source: 'https://www.wowhead.com/tbc/guide/gruul-dragonkiller-gruuls-lair-strategy-burning-crusade-classic', abilities: [
    { name: 'Hurtful Strike', danger: 'tank', summary: 'Hits the second-highest threat target; an off-tank must maintain threat and survive the strike.' },
    { name: 'Ground Slam / Shatter', danger: 'position', summary: 'Knockback followed by heavy area damage; spread after the slam so Shatter does not chain through the raid.' },
    { name: 'Cave In', danger: 'position', summary: 'Persistent ground damage; move out of the marked area.' },
    { name: 'Growth', danger: 'tank', summary: 'Periodic stacking damage increase. Later tank hits become progressively more dangerous.' },
  ] },
  { aliases: ["kael'thas", 'kaelthas'], era: 'TBC', raid: 'Tempest Keep: The Eye', summary: 'Multi-phase council encounter followed by Kael’thas. Control advisors, weapons, phoenixes, and the Shock Barrier / Pyroblast sequence.', health: 'Mode-specific', healthNote: 'Several phases and add health pools; check the linked guide for the matching TBC tuning.', source: 'https://www.wowhead.com/tbc/guide/kaelthas-sunstrider-the-eye-tempest-keep-strategy-burning-crusade-classic', abilities: [
    { name: 'Fireball', danger: 'tank', summary: 'Heavy fire hit on the tank; interrupt where possible and keep the active tank stable.' },
    { name: 'Shock Barrier / Pyroblast', danger: 'interrupt', summary: 'Break the barrier quickly and coordinate interrupts or defensive cooldowns for Pyroblast.' },
    { name: 'Flamestrike', danger: 'position', summary: 'Ground-targeted fire damage; leave the impact area promptly.' },
    { name: 'Phoenix / Egg', danger: 'raid', summary: 'Kill the phoenix and then its egg before it revives.' },
  ] },
  { aliases: ['prince malchezaar', 'malchezaar'], era: 'TBC', raid: 'Karazhan', summary: 'Three phases with increasing threat and raid pressure; Infernals create persistent safe-area constraints.', health: 'Mode-specific', healthNote: 'Karazhan health and damage depend on the version and tuning.', source: 'https://www.wowhead.com/tbc/guide/prince-malchezaar-karazhan-strategy-burning-crusade-classic', abilities: [
    { name: 'Enfeeble', danger: 'raid', summary: 'Reduces several players to very low health; healers should be ready for the follow-up damage.' },
    { name: 'Shadow Nova', danger: 'position', summary: 'Close-range knockback and shadow damage; ranged players should stay out of its radius.' },
    { name: 'Infernal / Hellfire', danger: 'position', summary: 'Infernals land in the room and create damaging zones; reposition the raid as space is lost.' },
  ] },
  { aliases: ['rage winterchill', 'winterchill'], era: 'TBC', raid: 'Hyjal Summit', summary: 'Single-phase lich encounter after the wave event. Random Icebolt targets need fast healing; players must leave Death and Decay.', health: '~2 million (historical TBC NPC estimate)', healthNote: 'Approximate historical estimate, not measured from the selected report; verify against the deployed TBC build.', source: 'https://www.wowhead.com/tbc/guide/rage-winterchill-hyjal-summit-strategy-burning-crusade-classic', abilities: [
    { name: 'Icebolt', danger: 'raid', summary: 'Random target takes 4,250–5,750 Frost damage, then 2,500 damage per second for 4 seconds while stunned.' },
    { name: 'Death and Decay', danger: 'position', summary: 'Ground area deals 15% of each player’s maximum health as Shadow damage per second; move out quickly.' },
    { name: 'Frost Nova', danger: 'raid', summary: 'Nearby players are rooted and take about 2,775 Frost damage; dispel/positioning can affect the follow-up.' },
    { name: 'Frost Armor', danger: 'tank', summary: 'Increases the boss’s armor and frost resistance and slows melee attackers.' },
  ] },
  { aliases: ['anetheron'], era: 'TBC', raid: 'Hyjal Summit', summary: 'Spread healers and ranged players against Carrion Swarm; assign an off-tank and healer to each Infernal.', health: 'Mode-specific', healthNote: 'A reliable, mode-matched maximum-health figure is not included in this report.', source: 'https://www.wowhead.com/tbc/guide/anetheron-hyjal-summit-strategy-burning-crusade-classic', abilities: [
    { name: 'Carrion Swarm', danger: 'raid', summary: 'Cone hits for about 4,250 Shadow damage and reduces healing done by affected players by 75% for 20 seconds.' },
    { name: 'Inferno', danger: 'tank', summary: 'Summons a Towering Infernal at a random player. An off-tank should pick it up quickly; its aura deals heavy fire damage.' },
    { name: 'Sleep', danger: 'raid', summary: 'Sleeps three random players; damage wakes them, so watch for overlapping Infernal damage.' },
    { name: 'Vampiric Aura', danger: 'tank', summary: 'Anetheron heals from melee damage he deals. A healing-reduction effect limits this sustain.' },
  ] },
  { aliases: ["kaz'rogal", 'kazrogal'], era: 'TBC', raid: 'Hyjal Summit', summary: 'Mana users manage the escalating Mark drain while the raid handles a frontal cleave and close-range stun.', health: 'Mode-specific', healthNote: 'A reliable, mode-matched maximum-health figure is not included in this report.', source: 'https://www.wowhead.com/tbc/guide/kazrogal-hyjal-summit-strategy-burning-crusade-classic', abilities: [
    { name: 'Mark of Kaz’rogal', danger: 'raid', summary: 'Drains 600 mana per second for 5 seconds. Players unable to pay the drain explode for about 10,213–11,287 damage in a 15-yard radius.' },
    { name: 'War Stomp', danger: 'raid', summary: 'Nearby players and NPCs are stunned for 5 seconds and take about 2,000 damage.' },
    { name: 'Malevolent Cleave', danger: 'position', summary: 'Frontal cleave is split among targets hit; keep the raid out of the boss’s front.' },
  ] },
  { aliases: ['azgalor'], era: 'TBC', raid: 'Hyjal Summit', summary: 'Tank swaps and add pickup matter while Doom marks a player for death; position the raid to control Rain of Fire.', health: 'Mode-specific', healthNote: 'A reliable, mode-matched maximum-health figure is not included in this report.', source: 'https://www.wowhead.com/tbc/guide/azgalor-hyjal-summit-strategy-burning-crusade-classic', abilities: [
    { name: 'Doom', danger: 'raid', summary: 'Marks a random player; the target dies after 20 seconds unless the encounter response removes or transfers the threat.' },
    { name: 'Rain of Fire', danger: 'position', summary: 'Ground-targeted fire damage; move out and avoid carrying the effect through the raid.' },
    { name: 'Howl of Azgalor', danger: 'raid', summary: 'Silences the raid and can interrupt healing during heavy tank damage.' },
    { name: 'Doomguard', danger: 'tank', summary: 'A Doomguard joins the fight; an assigned off-tank should control it promptly.' },
  ] },
  { aliases: ['archimonde'], era: 'TBC', raid: 'Hyjal Summit', summary: 'Survival-focused single-target fight. Fear can send players into Doomfire; Air Burst requires the Tears of the Goddess to prevent lethal falling damage.', health: '~4.5–4.9 million (historical estimates)', healthNote: 'Published historical estimates vary. Treat this as a rough reference only; the report does not provide maximum boss health.', source: 'https://www.wowhead.com/tbc/guide/archimonde-hyjal-summit-strategy-burning-crusade-classic', abilities: [
    { name: 'Doomfire', danger: 'position', summary: 'Persistent fire follows a player; standing in it deals about 2,400 Fire damage per second and applies a damaging debuff.' },
    { name: 'Fear', danger: 'raid', summary: 'Raid-wide fear lasts about 8 seconds. Fear protection and space away from Doomfire reduce chain deaths.' },
    { name: 'Air Burst', danger: 'raid', summary: 'Target and nearby players take about 3,000 Nature damage and are launched; use Tears of the Goddess to survive the fall.' },
    { name: 'Grip of the Legion', danger: 'raid', summary: 'Curse deals about 2,500 Shadow damage every 2 seconds; decurse quickly.' },
    { name: 'Finger of Death', danger: 'tank', summary: 'If no one is in melee range, a random player takes about 20,000 Shadow damage.' },
  ] },
  { aliases: ['ragnaros'], era: 'Classic', raid: 'Molten Core', summary: 'Fire-focused encounter with knockbacks, raid control, and a Son of Flame intermission.', health: 'Version-specific', healthNote: 'Classic/Seasonal variants do not share one reliable health value; see the NPC page for its displayed mode.', source: 'https://www.wowhead.com/classic/guide/ragnaros-molten-core-strategy-wow-classic', abilities: [
    { name: 'Wrath of Ragnaros', danger: 'tank', summary: 'Fire knockback against nearby targets; tank positioning and fire resistance affect the response.' },
    { name: 'Lava Burst', danger: 'raid', summary: 'Ranged fire attack against mana users; spread and heal the affected players.' },
    { name: 'Magma Blast', danger: 'tank', summary: 'Punishes missing or insufficient threat on the boss.' },
    { name: 'Sons of Flame', danger: 'raid', summary: 'Intermission adds must be controlled and killed before Ragnaros returns.' },
  ] },
  { aliases: ['onyxia'], era: 'Classic', raid: "Onyxia's Lair", summary: 'Three phases: frontal and tail attacks on the ground, deep breath while airborne, then fear and whelps on landing.', health: 'Version-specific', healthNote: 'Health differs between original Classic and Seasonal modes; check the linked guide/NPC page.', source: 'https://www.wowhead.com/classic/guide/onyxia-onyxias-lair-strategy-wow-classic', abilities: [
    { name: 'Flame Breath / Tail Sweep', danger: 'position', summary: 'Frontal fire and rear knockback; keep the raid along her side.' },
    { name: 'Wing Buffet', danger: 'tank', summary: 'Knocks back and reduces threat; tank against the wall and manage threat resets.' },
    { name: 'Deep Breath', danger: 'raid', summary: 'Air-phase fire breath across the chamber; track her position and move out of its path.' },
    { name: 'Bellowing Roar / Whelps', danger: 'raid', summary: 'Landing phase fear can trigger whelp problems; control the adds and protect the tank.' },
  ] },
  { aliases: ['nefarian'], era: 'Classic', raid: 'Blackwing Lair', summary: 'Adds in phase one, dragon phase two, then resurrected adds at 20%; class calls change the raid response.', health: 'Version-specific', healthNote: 'Check the linked NPC page for the exact Classic mode and raid size.', source: 'https://www.wowhead.com/classic/npc=11583/nefarian', abilities: [
    { name: 'Shadowflame', danger: 'raid', summary: 'Frontal shadow fire; dragon positioning and the Onyxia Scale Cloak are central to survival.' },
    { name: 'Class Calls', danger: 'raid', summary: 'Each call changes behavior for one class; identify the call and adjust immediately.' },
    { name: 'Fear / Tail Lash', danger: 'position', summary: 'Control and displacement can destabilize the tank and raid positioning.' },
    { name: 'Phase Three adds', danger: 'raid', summary: 'Dead Drakonids rise again at 20%; prepare area damage and control.' },
  ] },
  { aliases: ['magmadar'], era: 'Classic', raid: 'Molten Core', summary: 'Core Hound boss built around periodic fear and fire damage.', health: 'Version-specific', healthNote: 'Check the linked Classic NPC/encounter guide for the applicable mode.', source: 'https://www.wowhead.com/classic/npc=11982/magmadar', abilities: [
    { name: 'Panic', danger: 'raid', summary: 'Raid fear; fear prevention and healer positioning help keep the tank stable.' },
    { name: 'Lava Bomb', danger: 'position', summary: 'Fire damage around targeted players; spread and move from the impact area.' },
    { name: 'Frenzy', danger: 'tank', summary: 'Increases attack speed; tranq shot timing and tank cooldowns reduce the burst.' },
  ] },
]

export function bossGuideFor(name: string): BossGuide | undefined {
  const normalized = name.toLocaleLowerCase().replace(/[^a-z0-9]/g, '')
  return BOSS_GUIDES.find((guide) => guide.aliases.some((alias) => normalized.includes(alias.toLocaleLowerCase().replace(/[^a-z0-9]/g, ''))))
}
