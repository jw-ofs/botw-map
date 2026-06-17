/* Hand-authored combat data for overworld foes, keyed by the marker name
   (which is the enemy type). Rendered in popups: weaknesses, damage dealt, a tip. */
window.BOSSDATA = {
  "Hinox": {
    weak: ["Eye (arrows)", "Climbing"],
    deals: ["💥 Physical"],
    tip: "One big eye — an arrow to it staggers the Hinox; pile on while it's down. You can pluck the weapons hanging from its necklace. Sleeping ones can be looted or hit for a free opener.",
  },
  "Stone Talus": {
    weak: ["Ore on its body", "Hammers / two-handers"],
    deals: ["💥 Physical"],
    tip: "Climb on and smash the black ore deposit (its weak point) with a hammer or two-handed weapon. Elemental variants — Igneo (fire) and Frost — are weak to the opposite element; douse/melt them first.",
  },
  "Molduga": {
    weak: ["Bomb Arrows", "Remote Bombs"],
    deals: ["💥 Physical"],
    tip: "It 'swims' through sand and lunges at movement. Set off a Remote Bomb to make it surface and flip, then attack the exposed body. Fight from a rock outcrop it can't reach.",
  },
  "Guardian Stalker": {
    weak: ["Ancient Arrow → eye (instant kill)", "Shield parry"],
    deals: ["🔆 Laser", "💥 Physical"],
    tip: "An Ancient Arrow to the eye one-shots it. Otherwise shoot/sever the six legs to immobilize, or perfectly time a shield parry to reflect the blue laser back for huge damage.",
  },
  "Guardian Turret": {
    weak: ["Ancient Arrow → eye", "Shield parry"],
    deals: ["🔆 Laser"],
    tip: "Wall/ceiling-mounted and immobile. Shoot the eye, climb up to strike it in melee, or parry its laser. Common inside shrines and dungeons.",
  },
  "Guardian Skywatcher": {
    weak: ["Ancient Arrow → eye"],
    deals: ["🔆 Laser", "💣 Bombs"],
    tip: "Flies and drops bombs. Shoot the eye to knock it out of the sky, then finish it on the ground. Ancient Arrows end it instantly.",
  },
  "Decayed Guardian": {
    weak: ["Eye", "Working legs / arms"],
    deals: ["🔆 Laser"],
    tip: "Half-buried but many still fire the beam. Destroy the eye to kill it; break any still-moving legs or arms first to stop it tracking you.",
  },
  "Lynel": {
    weak: ["Headshot → mount", "Flurry rush"],
    deals: ["💥 Physical"],
    tip: "Shock-arrow (or any arrow) to the face stuns it — sprint up and mount for free hits, then perfect-dodge its lunge for flurry rushes. The base red Lynel is the weakest tier.",
  },
  "Blue-Maned Lynel": {
    weak: ["Headshot → mount", "Flurry rush"],
    deals: ["💥 Physical", "🔥 Fire arrows"],
    tip: "Tougher than red. Same loop: headshot stun → mount → flurry rush. Bring durable weapons; it shrugs off light hits.",
  },
  "White-Maned Lynel": {
    weak: ["Headshot → mount", "Flurry rush"],
    deals: ["💥 Physical", "⚡ Shock"],
    tip: "High HP and damage. Strong weapons and a few fairies recommended. Open with a headshot, mount, and chain flurry rushes on its charge.",
  },
  "Silver Lynel": {
    weak: ["Headshot → mount", "Flurry rush"],
    deals: ["💥 Physical", "Elemental"],
    tip: "The deadliest overworld enemy. Same stun-mount-flurry loop, but it hits brutally hard — Mighty/Enduring food and Fairies strongly advised. Drops the best Lynel gear.",
  },
  "Dinraal": {
    weak: [],
    deals: ["🔥 Fire"],
    tip: "Fire dragon — circuits Eldin & the Tabantha Frontier (appears at night, flies up Tanagar Canyon at dawn). Don't fight it: shoot a horn, claw, scale, or fang for crafting parts. Paraglide alongside to line up shots.",
  },
  "Farosh": {
    weak: [],
    deals: ["⚡ Electric"],
    tip: "Electric dragon — circuits Faron and the Gerudo Highlands lake. Shoot a body part for materials; it periodically discharges shock, so fire and then back off. Horn shards are the rarest drop.",
  },
  "Naydra": {
    weak: [],
    deals: ["❄️ Ice"],
    tip: "Ice dragon — circuits Lanayru and Mount Lanayru (first freed of Malice during the Spring of Wisdom). Shoot horns/claws/scales/fang for parts. Approach by paraglider from a high ledge.",
  },
};
