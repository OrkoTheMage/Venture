# ── Quest lore ────────────────────────────────────────────────────────────── #
QUEST_LORE: dict[str, str] = {
    "Gather Allies": (
        "The estate has fallen. The roster is thin — a sorry few against the darkness that "
        "gathers at the edges of the world. Word comes of capable souls willing to pledge steel "
        "and prayer to your cause, if you can prove yourself worthy of their service. "
        "Go. Bring them into the fold."
    ),
    "The Family Business": (
        "Beneath the ancestral estate, sealed behind iron doors and rusted locks, lies a library "
        "of terrible consequence. The signet ring rests within — proof of your birthright, your "
        "claim to lordship. What else rests within, you dare not yet consider. "
        "Descend. Reclaim what is yours, if you have the stomach for it."
    ),
    "Sins of the Father": (
        "The Signet Ring grows cold in your possession. It remembers what you have tried to forget. "
        "There are rooms in the estate that were locked before you were born — rooms your father "
        "kept locked, and his father before him. Something old has been waiting behind those doors. "
        "Something patient. Something that knows your name. "
        "Face what your bloodline made. End it, or be undone by it."
    ),
    "Haunted Mill": (
        "The millstone has gone silent. Grain rots in the fields, and those sent to investigate "
        "have not returned. The villagers whisper of grinding sounds in the dead of night — "
        "and pale, lurching shapes pressed against the darkened windows. "
        "What hunger turns the mill now? Go. Find out. End it."
    ),
    "Bandit Ambush": (
        "The eastern road runs red with merchant blood. Violent cutthroats have seized the "
        "highway, preying upon travelers with sword and cruelty unchecked. Commerce has ceased. "
        "Fear has taken root in honest men. Root it out in turn — and remind them "
        "what true fear tastes like."
    ),
    "Deep Cavern": (
        "The prospectors sent word of rich ore veins — then sent nothing at all. The Thornwall "
        "tunnels have swallowed men before, but something stirs in the deep dark now. "
        "Ancient. Patient. Hungry. Delve the cavern. Find what silenced them."
    ),
    "Cursed Tomb": (
        "A raving wretch crawled from the hills speaking of walking dead and shattered seals. "
        "The runes of binding have weakened — that which was entombed stirs once more, and the "
        "very earth trembles with its restlessness. Enter the tomb. Put it back down. "
        "If such a thing is still possible."
    ),
    "Goblin Warrens": (
        "The tunnels spread beneath the farmlands like a festering wound in the earth. "
        "The goblin tribe grows bold — their raids more frequent, their savagery more brazen "
        "with each passing season. The harvest withers. The villages starve. "
        "Descend into their filth and wipe them out."
    ),
    "Abandoned Tower": (
        "For a decade the tower stood dark and silent on the headlands. Last week, strange "
        "lights flickered in the uppermost window. Arcane sounds drifted across the cliffs "
        "in the dead of night. Something has claimed the scholar's tower — "
        "and the dangerous knowledge within it. Take it back."
    ),
    "Plague Village": (
        "Duskhollow has gone quiet under a creeping and malignant sickness. Survivors speak of "
        "shambling figures and a foul miasma rolling in from the east — a corruption that rots "
        "the flesh and unhinges the mind alike. Investigate the source. "
        "Smother it before it spreads further afield."
    ),
    "Sunken Temple": (
        "The fishermen pulled carved stones from the deep — remnants of a temple the sea had "
        "claimed long ago. Now the tide recedes and ancient walls rise once more, filled with "
        "salt water and older, fouler things. The temple hungers. "
        "Do not let it feed unopposed."
    ),
    "Highroad Ambush": (
        "The king's road belongs to fear. A brutal crime lord has seized the highway, "
        "extorting merchants and murdering those who dare refuse to kneel. Commerce has "
        "choked. Word of justice has grown bitter in the mouth. Clear the road. "
        "Scatter the gang. Press on, regardless."
    ),
    "Glacial Keep": (
        "A fortress locked in ice since the Age of Frost has begun to thaw. Something "
        "imprisoned in that frozen hell stirs for the first time in centuries — its patience "
        "rewarded at last by the warming dark. Reach it before it frees itself. "
        "Before your rivals do. Before it is too late for either."
    ),
    "Undead Mire": (
        "The marshes east of Brackenveil swarm with restless dead, drawn forth from forgotten "
        "graves by some malign will at the marsh's black heart. A collapsed shrine. "
        "An old and wicked magic. Destroy the source and put the dead to rest — "
        "before more join their shambling number."
    ),
    "Iron Mine": (
        "The Ironpeak mine collapsed three months past. The workers who survived the cave-in "
        "were pulled free from the rubble. They should have stayed buried. "
        "Investigate what they found in the dark below — and deal with it, "
        "before it deals with the surface world on its own terms."
    ),
    "Arcane Ruins": (
        "Ancient ruins crackle with unstable and hungry magic, drawing desperate sorcerers "
        "like moths to a funeral pyre. Their experiments tear at the very fabric of reality. "
        "Left unchecked, the rift they seek to open will devour everything. "
        "Every last wretched thing."
    ),
    "Cult Gathering": (
        "Villagers vanish in the night — taken by a hidden cult conducting dark rites upon "
        "the moors. A single survivor crawled free, broken but breathing, clutching word of "
        "their gathering place. The ritual nears its terrible conclusion. "
        "Strike now, or do not bother striking at all."
    ),
    "Burning Village": (
        "Ashford burns. A mercenary company, unmoored from conscience and contract alike, "
        "has turned its blades upon the very people it was hired to protect. Survivors flee "
        "the flames screaming of slaughter. Ride hard. Save what can be saved. "
        "Avenge what cannot."
    ),
}

# ── Quest definitions ─────────────────────────────────────────────────────── #
INITIAL_QUEST = [
    {"name": "Gather Allies", "danger": 1, "length": "Short", "enemies": "Physical"},
]

# ── Boss quests ───────────────────────────────────────────────────────────── #
BOSS_QUEST_FAMILY_BUSINESS = {
    "name": "The Family Business",
    "danger": 3,
    "length": "Medium",
    "enemies": "Horror",
    "boss": True,
}

BOSS_QUEST_SINS_OF_THE_FATHER = {
    "name": "Sins of the Father",
    "danger": 5,
    "length": "Medium",
    "enemies": "Horror",
    "boss": True,
}

# Pool of named quests with fixed enemy types — danger & length are randomized at roll time
QUEST_POOL = [
    {"name": "Haunted Mill",           "enemies": "Horror"},
    {"name": "Bandit Ambush",          "enemies": "Physical"},
    {"name": "Deep Cavern",            "enemies": "Physical/Magic"},
    {"name": "Cursed Tomb",            "enemies": "Horror"},
    {"name": "Goblin Warrens",         "enemies": "Physical"},
    {"name": "Abandoned Tower",        "enemies": "Magic"},
    {"name": "Plague Village",         "enemies": "Horror/Physical"},
    {"name": "Sunken Temple",          "enemies": "Magic"},
    {"name": "Highroad Ambush",        "enemies": "Physical"},
    {"name": "Glacial Keep",           "enemies": "Physical/Magic"},
    {"name": "Undead Mire",            "enemies": "Horror"},
    {"name": "Iron Mine",              "enemies": "Physical"},
    {"name": "Arcane Ruins",           "enemies": "Magic"},
    {"name": "Cult Gathering",         "enemies": "Horror/Magic"},
    {"name": "Burning Village",        "enemies": "Physical"},
]
