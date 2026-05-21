from __future__ import annotations

from ..utils.format import render_lore, lore_line_count  # noqa: F401 — re-exported for callers

# ── Location event pool (75% chance) ─────────────────────────────────────── #
EVENTS: list[dict] = [
    {
        "name":     "Bountiful Harvest",
        "location": "The Farmlands",
        "effect":   "heal",
        "lore": (
            "Farmers bring a cartload of hard-won grain to the estate, asking only for willing steel against the dark things gnawing at their fields. "
            "Those who answer find their wounds somehow lighter upon return."
        ),
        "effect_desc": "Heal 25% max HP on quest completion in The Farmlands",
    },
    {
        "name":     "Rich Veins",
        "location": "The Mountains",
        "effect":   "gold",
        "lore": (
            "Word comes down from the stonecutters — the high passes are flush with forgotten coin, old hoards swallowed by collapse long before your grandfather drew breath. "
            "The diggers dare not venture far alone, but those who do return with considerably heavier purses."
        ),
        "effect_desc": "Earn 100% more gold on quest completion in The Mountains",
    },
    {
        "name":     "Creeping Revelation",
        "location": "The Moors",
        "effect":   "exp",
        "lore": (
            "A strange mist has settled over the moors — the kind that sharpens the mind and makes plain what was murk. "
            "Those who walk through it return older behind the eyes, carrying wisdom that came more swiftly than it ought."
        ),
        "effect_desc": "Earn 100% more EXP on quest completion in The Moors",
    },
    {
        "name":     "The Arcane Tide",
        "location": "The Lochs",
        "effect":   "spell_recharge",
        "lore": (
            "The water at the lochs shifts against the current — silver-cold and humming with something older than the estate, older than the name you carry. "
            "Wizards touched by it feel their exhausted spells stir and rekindle, as though the night has decided to grant them another chance."
        ),
        "effect_desc": "All spells recharge for one random Wizard after a quest in The Lochs",
    },
]

# ── Town event pool (24% chance) ─────────────────────────────────────────── #
TOWN_EVENTS: list[dict] = [
    {
        "name":       "A Moment of Respite",
        "location":   None,
        "effect":     "respite",
        "town_event": True,
        "lore": (
            "A rare stillness has settled over the estate — the fragile quiet of good fortune and open hands. "
            "Wounds will be mended, and the coins in the coffers will stack up nicely. Rest easy, this week brings good tidings."
        ),
        "effect_desc": "After any quest: +10% HP, +50% gold and EXP",
    },
    {
        "name":       "Read The Bones",
        "location":   None,
        "effect":     "bones",
        "town_event": True,
        "lore": (
            "A bone-reader arrived at the gates before dawn, asking neither coin nor courtesy. "
            "She named two from the next party — one who would pass through untouched, and one who would bear the full weight of what waits within."
        ),
        "effect_desc": "One random hero takes max damage, one takes none",
    },
    {
        "name":       "The Shaded Carriage",
        "location":   None,
        "effect":     "carriage",
        "town_event": True,
        "lore": (
            "A covered carriage rolled in before midnight, its driver hooded and unhurried. "
            "Those within are available this week at prices that will not hold. Bolster the ranks — few are so willing to throw their lives into this chaos."
        ),
        "effect_desc": "Recruit slot 2 is free, slot 3 is 50% off",
    },
    {
        "name":       "Thieves in the Night",
        "location":   None,
        "effect":     "thieves",
        "town_event": True,
        "lore": (
            "Before the first candle was lit, a ring of cutpurses worked their way through the estate "
            "— drawers forced, locks picked, and storeroom supplies left bare. "
            "They are still close. The trail is still warm. "
            "Leave them to it, and they'll make with your hard-earned fortunes."
        ),
        "effect_desc": "A boss quest appears in slot 1 — clear it for +50% gold, ignore it and lose 50%",
    },
]

# ── Rare event pool (1% chance) ──────────────────────────────────────────── #
RARE_EVENTS: list[dict] = [
    {
        "name":       "An Old Ally",
        "location":   None,
        "effect":     "banner_man",
        "rare_event": True,
        "lore": (
            "An old soldier arrived at the estate gate before sunrise, bearing a standard you almost didn't recognise — your family's colours, faded and battle-worn. "
            "They ask for no coin, only purpose, and they are clearly capable of far more than most your gold could buy."
        ),
        "effect_desc": "A 4th recruit appears this week — level 5 and free",
    },
    {
        "name":       "Returned From The Styx",
        "location":   None,
        "effect":     "styx",
        "rare_event": True,
        "lore": (
            "Word arrived in the grey hours — a name spoken on the other side of the dark, too stubborn to stay. "
            "One among the fallen has found their way back to the threshold, and the door stands open if you choose to call them through."
        ),
        "effect_desc": "Revive one hero from the graveyard",
    },
    {
        "name":       "Dark Ritual",
        "location":   None,
        "effect":     "ritual",
        "rare_event": True,
        "lore": (
            "A hooded figure came to the estate in silence, offering knowledge wrapped in shadow and cost. "
            "One of your heroes may be taken aside before dawn and returned changed — harder, carrying a level of capability that was not theirs before."
        ),
        "effect_desc": "Choose one hero to gain 1 level",
    },
    {
        "name":       "For Whom The Bell Tolls",
        "location":   None,
        "effect":     "bell_tolls",
        "rare_event": True,
        "lore": (
            "The bell in the estate tower rang out once at the black hour — no hand pulled the rope, no wind stirred the air. "
            "In the old reckoning, such a toll was not for any one soul. It rang for all. "
            "The weight of suffering, parcelled quietly across every living body on the grounds. "
            "By morning the wounds had closed. What it cost, and who paid it, the bell does not say."
        ),
        "effect_desc": "Every hero in the roster is healed to full",
    },
]

# ── Combined pool — indices 0-3 location, 4-7 town, 8-11 rare ────────────── #
ALL_EVENTS: list[dict] = EVENTS + TOWN_EVENTS + RARE_EVENTS
