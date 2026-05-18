from __future__ import annotations

import textwrap


def render_lore(lore: tuple[str, str] | str, width: int, indent: str = "  ") -> list[str]:
    """Return display lines for a lore entry. The bold ending is rendered bold."""
    if isinstance(lore, str):
        return [f"{indent}{ln}" for ln in textwrap.wrap(lore, width=max(20, width))]
    body, bold = lore
    lines: list[str] = []
    if body:
        lines += [f"{indent}{ln}" for ln in textwrap.wrap(body, width=max(20, width))]
    if bold:
        lines += [f"{indent}\033[1m{ln}\033[0m" for ln in textwrap.wrap(bold, width=max(20, width))]
    return lines


def lore_line_count(lore: tuple[str, str] | str, width: int) -> int:
    """Return the number of wrapped display lines for a lore entry."""
    return len(render_lore(lore, width, indent=""))


# ── Quest lore ────────────────────────────────────────────────────────────── #
QUEST_LORE: dict[str, tuple[str, str]] = {
    # ── Estate ────────────────────────────────────────────────────────────── #
    "Thieves in the Night": (
        "You follow the trail of burnt midnight oil and loose coins. It ends just outside the estate's grounds, "
        "where you find a shoddy camp of ragged indigents, brigands, and robbers. "
        "\033[1mSnuff them out. This will likely be your last chance. Reclaim what is yours.\033[0m",
        ""
    ),
    "Gather Allies": (
        "The estate has fallen. Your roster is thin — a sorry few against the darkness that "
        "gathers at the edges of the world. Word spreads of capable souls willing to pledge steel, "
        "knowledge, and prayer to your cause if you can prove yourself worthy of their service.",
        "Go. Bring them into the fold."
    ),
    "The Family Business": (
        "Beneath the ancestral estate, sealed behind iron doors and rusted locks, lies a library "
        "of terrible consequence. Your family's signet ring rests within — proof of your birthright, "
        "your claim to lordship. What else lies there, you dare not yet consider.",
        "Descend. Reclaim what is yours, if you have the stomach for it."
    ),
    "Sins of the Father": (
        "The Signet Ring grows cold in your possession. It remembers what you have tried to forget. "
        "There are rooms under the estate that were locked before you were born — rooms your father "
        "kept locked, and his father before him. Something old has been waiting behind those doors. "
        "Something patient. Something that knows your name.",
        "Face what your bloodline made. End it, or be undone by it."
    ),
    # ── The Farmlands ─────────────────────────────────────────────────────── #
    "Goblin Warrens": (
        "The tunnels spread beneath the farmlands like a festering wound in the earth. "
        "The goblin tide grows bold — their raids more frequent, their savagery more brazen "
        "with each passing season.",
        "The harvest withers. The villagers starve. Descend into their filth and wipe them out."
    ),
    "Plagued Village": (
        "The neighboring village has gone quiet under a creeping and malignant sickness. "
        "Survivors speak of shambling figures and a foul miasma rolling on the winds — "
        "a corruption that rots the flesh and unhinges the mind alike.",
        "Investigate the source. Smother it before it spreads further afield."
    ),
    "Haunted Mill": (
        "The millstone has gone silent. Grain rots in the fields, and those sent to investigate "
        "have not returned. The villagers whisper of grinding sounds in the dead of night — "
        "and pale, lurching shapes pressed against the darkened windows.",
        "What hunger turns the mill now? Go. Find out. End it."
    ),
    "The Pretender-King's Regicide": (
        "A crown of rust and dried blood sits on a goblin head, and beneath it blinks something "
        "that calls itself a king. The warrens have unified — an ugly, screaming, inexplicable "
        "nation of goblins that has turned the farmlands into tribute grounds. The harvest rots. "
        "The villagers pay in flesh for what they cannot pay in grain.",
        "A pretender on a throne is still just a pretender. Remind him, with steel."
    ),
    # ── The Moors ─────────────────────────────────────────────────────────── #
    "Cult Gathering": (
        "Villagers vanish in the night — taken by a hidden cult conducting dark rites upon "
        "the moors. A single survivor crawled free, broken but breathing, clutching word of "
        "their gathering place. The ritual nears its terrible conclusion.",
        "The final hours are nigh. Strike now, before it is too late."
    ),
    "Witches' Hollow": (
        "The heather burns cold on the high moor — not with fire, but with arcane light that "
        "leaves no ash. The villages speak of women who walk against the wind, of hexes that "
        "curdle the milk and wither the newborn. Something older than scripture is being "
        "practised in the hollows beyond the standing stones.",
        "Find what they worship. Silence the rite before it is answered."
    ),
    "The Hungry Mire": (
        "The moor path has been swallowed. Not by water — by something that grows. Tendrils "
        "as thick as a man's arm curl from the bogwater, and shapes that were once farmhands "
        "move between carnivorous blooms with glassy eyes and open mouths. Three search "
        "parties went in. None returned. Something tends that garden.",
        "Root it out before the garden claims the next village whole."
    ),
    "The Shepherd's Slaughter": (
        "The moors have a shepherd. He keeps no flock of wool and mutton — his flock shuffles "
        "through the fog in silence, hollow-eyed and obedient without thought. If there is a "
        "figurehead to the rites and rituals being conducted in those murky waters, it's him. "
        "He must not be allowed to complete whatever terrible ceremony he has been building "
        "towards in the dark.",
        "Find him. End his flock. Cull the Shepherd."
    ),
    # ── The Mountains ─────────────────────────────────────────────────────── #
    "Glacial Keep": (
        "A fortress locked in ice, once still to time itself, has begun to thaw. Something "
        "imprisoned in that frozen hell stirs for the first time in centuries — its patience "
        "rewarded at last by the warming dark.",
        "Reach it before it frees itself. Before your rivals do. Before it is too late for either."
    ),
    "Iron Mine": (
        "The northern iron mines collapsed three months past. The workers who survived the "
        "cave-in were pulled free from the rubble. Whatever they uncovered in those blackened "
        "arcades should have stayed buried.",
        "Investigate what they found in the dark below — and deal with it, before it manifests on its own terms."
    ),
    "Deep Caverns": (
        "The prospectors sent word of rich ore veins — then sent nothing at all. The deep "
        "caverns and tunnels within the northern mountains have swallowed men before, but "
        "something stirs in the deep dark now.",
        "Ancient. Patient. Hungry. Delve the caverns. Find what silenced them."
    ),
    "The Warden's Watch Ends": (
        "The Glacial Keep has a guardian. Neither alive nor cleanly dead — a thing of old iron "
        "and older runes, bound to its post by a compact carved before the kingdom had a name. "
        "The mine collapses, the disappearances on the mountain passes, everything can be traced "
        "back to that damned Keep. The Warden has been woken by something, and now it allows "
        "nothing to pass.",
        "Find it. Break the compact. Put it down before the entire mountain range becomes its ward."
    ),
    # ── The Lochs ─────────────────────────────────────────────────────────── #
    "Sunken Temple": (
        "The fishermen pulled carved stones from the deep — remnants of a temple the sea had "
        "claimed long ago. Now the tide recedes, and ancient walls rise once more, filled with "
        "salt water and older, fouler things.",
        "The temple stands. Do not let it stand unopposed."
    ),
    "Corsair's Cove": (
        "The cove stinks of burning pitch and stolen gold. A corsair fleet — unmoored from any "
        "port that would claim them — has planted its flag on the lochside cliffs, raiding "
        "our fishing villages with cannon and cutlass alike. The fishermen cannot work, "
        "and the shoreline villagers starve.",
        "Clear the cove. Send what's left of the fleet to the bottom."
    ),
    "Pelagic Nightmares": (
        "The fish-folk have grown bold, spawning out of their once-sunken ruins. Their raids "
        "are becoming organised — systematic, purposeful — as if directed by something vast "
        "and knowing beneath the water. Shrines to an old and nameless thing line the loch "
        "floor, and the villagers who are swept away in the night are not found again. Not whole.",
        "Find what drives them. Destroy them all."
    ),
    "The Drowned God's Rest": (
        "The fish-folk do not raid for sport. They raid for tribute — offerings hauled down "
        "into the black water for something far older and far larger than themselves. "
        "The sunken ruins are its temple. The antediluvian dark of the loch is its domain. "
        "For ten thousand years it slept, and now it wakes, drawn upward by the weight of devotion.",
        "Cleave your way into the heart of it all. Destroy it. If such a thing can be destroyed."
    ),
}

# ── Initial quest ─────────────────────────────────────────────────────────── #
INITIAL_QUEST = [
    {"name": "Gather Allies", "danger": 1, "length": "Short", "enemies": "Physical", "location": "The Estate"},
]

# ── Estate boss quests (milestone-gated) ─────────────────────────────────── #
BOSS_QUEST_THIEVES_IN_THE_NIGHT = {
    "name":     "Thieves in the Night",
    "danger":   3,
    "length":   "Short",
    "enemies":  "Physical",
    "location": "The Estate",
}

BOSS_QUEST_FAMILY_BUSINESS = {
    "name":     "The Family Business",
    "danger":   3,
    "length":   "Medium",
    "enemies":  "Magic/Horror",
    "boss":     True,
    "location": "The Estate",
}

BOSS_QUEST_SINS_OF_THE_FATHER = {
    "name":     "Sins of the Father",
    "danger":   5,
    "length":   "Medium",
    "enemies":  "Physical/Horror",
    "boss":     True,
    "location": "The Estate",
}

# ── Location radiant quest pools (3 per location) ────────────────────────── #
LOCATION_QUESTS: dict[str, list[dict]] = {
    "The Moors": [
        {"name": "Cult Gathering",  "enemies": "Physical"},
        {"name": "Witches' Hollow", "enemies": "Magic"},
        {"name": "The Hungry Mire", "enemies": "Horror"},
    ],
    "The Farmlands": [
        {"name": "Goblin Warrens",  "enemies": "Physical"},
        {"name": "Plagued Village", "enemies": "Magic"},
        {"name": "Haunted Mill",    "enemies": "Horror"},
    ],
    "The Mountains": [
        {"name": "Glacial Keep",    "enemies": "Magic"},
        {"name": "Iron Mine",       "enemies": "Physical"},
        {"name": "Deep Caverns",    "enemies": "Horror"},
    ],
    "The Lochs": [
        {"name": "Sunken Temple",       "enemies": "Magic"},
        {"name": "Corsair's Cove",      "enemies": "Physical"},
        {"name": "Pelagic Nightmares",  "enemies": "Horror"},
    ],
}

# ── Location boss quests (unlock at 5+ clears in that location) ──────────── #
LOCATION_BOSSES: dict[str, dict] = {
    "The Moors": {
        "name":     "The Shepherd's Slaughter",
        "danger":   5,
        "length":   "Medium",
        "enemies":  "Magic/Physical",
        "boss":     True,
        "location": "The Moors",
        "reward":   "Torn Tapestry",
    },
    "The Farmlands": {
        "name":     "The Pretender-King's Regicide",
        "danger":   5,
        "length":   "Medium",
        "enemies":  "Physical/Horror",
        "boss":     True,
        "location": "The Farmlands",
        "reward":   "Broken Crown",
    },
    "The Mountains": {
        "name":     "The Warden's Watch Ends",
        "danger":   5,
        "length":   "Medium",
        "enemies":  "Magic/Physical",
        "boss":     True,
        "location": "The Mountains",
        "reward":   "Frost Rune",
    },
    "The Lochs": {
        "name":     "The Drowned God's Rest",
        "danger":   5,
        "length":   "Medium",
        "enemies":  "Magic/Horror",
        "boss":     True,
        "location": "The Lochs",
        "reward":   "Drowned Idol",
    },
}
