"""
events.py — Weekly event definitions and effect application.

Each week one event is active. 75% chance of a location event, 25% town event.
Never repeats the previous week's event.
"""
from __future__ import annotations

import random

# ── Location event definitions (75% chance) ──────────────────────────────── #

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

# ── Town event definitions (25% chance) ──────────────────────────────────── #

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

# Combined pool — indices 0-3 location, 4-6 town, 7-8 rare
ALL_EVENTS: list[dict] = EVENTS + TOWN_EVENTS + RARE_EVENTS

# ── Active event ─────────────────────────────────────────────────────────── #

def get_active_event(week: int, state: dict | None = None) -> dict:
    """Return the active event. Uses stored index from state if available,
    otherwise falls back to week % len(EVENTS) (location events only)."""
    if state is not None and "active_event_idx" in state:
        return ALL_EVENTS[int(state["active_event_idx"]) % len(ALL_EVENTS)]
    return EVENTS[int(week) % len(EVENTS)]


def pick_next_event(state: dict) -> None:
    """Choose a new active event (never the same as the current one).
    75% location event, 24% town event, 1% rare event."""
    current_idx = int(state.get("active_event_idx", int(state.get("week", 0)) % len(EVENTS)))

    roll = random.random()
    loc_end   = len(EVENTS)                        # 0-3
    town_end  = len(EVENTS) + len(TOWN_EVENTS)     # 4-6
    # rare_end = len(ALL_EVENTS)                   # 7-8

    if roll < 0.75:
        pool = [i for i in range(loc_end) if i != current_idx]
    elif roll < 0.99:
        pool = [i for i in range(loc_end, town_end) if i != current_idx]
    else:
        pool = [i for i in range(town_end, len(ALL_EVENTS)) if i != current_idx]

    if not pool:
        pool = [i for i in range(len(ALL_EVENTS)) if i != current_idx]

    state["active_event_idx"] = random.choice(pool)

    # Clear any unused pending event from the previous week
    state.pop("pending_rare_event", None)

    # If the new event requires home-screen interaction, mark it as pending now
    new_event = ALL_EVENTS[state["active_event_idx"]]
    if new_event["effect"] == "styx" and state.get("graveyard"):
        state["pending_rare_event"] = "styx"
    elif new_event["effect"] == "ritual" and any(
        int(h.get("lvl", 1)) < 5 for h in state.get("roster", [])
    ):
        state["pending_rare_event"] = "ritual"


# ── Apply bonus ───────────────────────────────────────────────────────────── #

def apply_event_bonus(state: dict, quest_location: str, party_names: list[str] | None) -> list[str]:
    """
    Apply the active event's bonus after a quest completes.
    Location events only fire if the quest location matches.
    Town events (location=None) always fire.
    Reads active_event_idx directly from state (not yet advanced to next week).
    """
    event = get_active_event(0, state)

    # Location events: only apply if quest was in the matching location
    if event.get("location") and event["location"] != quest_location:
        return []

    effect = event["effect"]
    roster = state.get("roster", [])
    full_roster = state.get("_event_full_roster", roster)
    party_names_set = set(party_names) if party_names is not None else None
    party  = [h for h in roster if party_names_set is None or h["name"] in party_names_set]
    full_party = [h for h in full_roster if party_names_set is None or h["name"] in party_names_set]

    rewards: list[str] = []

    # ── Heal 25% max HP (Bountiful Harvest) ──────────────────────────────── #
    if effect == "heal":
        for h in party:
            max_hp = float(h.get("max_hp", 100))
            h["hp"] = min(max_hp, float(h.get("hp", max_hp)) + max_hp * 0.25)
        rewards.append(f"\033[32m[{event['name']}]\033[0m Party recovered \033[32m25% HP\033[0m")

    # ── 100% more gold (Rich Veins) ───────────────────────────────────────── #
    elif effect == "gold":
        bonus = int(state.get("_event_gold_base", 0) * 1.0)
        if bonus > 0:
            state["gold"] = int(state.get("gold", 0)) + bonus
            rewards.append(f"\033[32m[{event['name']}]\033[0m Found an extra \033[33m{bonus}G\033[0m in the mountain passes")

    # ── 100% more EXP (Creeping Revelation) ──────────────────────────────── #
    elif effect == "exp":
        bonus_exp = int(state.get("_event_exp_base", 0) * 1.0)
        if bonus_exp > 0:
            for h in party:
                if h["name"] in (state.get("_event_fallen", [])):
                    continue
                h["exp"] = int(h.get("exp", 0)) + bonus_exp
            rewards.append(
                f"\033[32m[{event['name']}]\033[0m The mist granted each hero an extra \033[36m{bonus_exp} EXP\033[0m"
            )

    # ── Recharge all spells for one random Wizard (The Arcane Tide) ──────── #
    elif effect == "spell_recharge":
        wizards_in_party = [
            h for h in full_party
            if h.get("class") == "Wizard"
        ]
        eligible_wizards = [h for h in wizards_in_party if int(h.get("lvl", 1)) > 1
                            and h["name"] not in state.get("_event_fallen", [])]
        if eligible_wizards:
            chosen = random.choice(eligible_wizards)
            cast_log = state.get("spell_cast_log", {})
            hero_log = cast_log.get(chosen["name"], {})
            hero_log.pop("mage_armor_until", None)
            hero_log.pop("alchemize_until", None)
            hero_log.pop("inspire_until", None)
            hero_log.pop("portal_until", None)
            cast_log[chosen["name"]] = hero_log
            state["spell_cast_log"] = cast_log
            rewards.append(
                f"\033[32m[{event['name']}]\033[0m The tide recharged all of {chosen['name']}'s spells"
            )
        elif wizards_in_party:
            lost = wizards_in_party[0]["name"]
            rewards.append(
                f"\033[32m[{event['name']}]\033[0m The tide's knowlege was lost on {lost}"
            )

    # ── +10% HP, +50% gold, +50% EXP (A Moment of Respite) ──────────────── #
    elif effect == "respite":
        for h in party:
            max_hp = float(h.get("max_hp", 100))
            h["hp"] = min(max_hp, float(h.get("hp", max_hp)) + max_hp * 0.10)
        bonus_gold = int(state.get("_event_gold_base", 0) * 0.5)
        bonus_exp  = int(state.get("_event_exp_base", 0) * 0.5)
        if bonus_gold > 0:
            state["gold"] = int(state.get("gold", 0)) + bonus_gold
        if bonus_exp > 0:
            for h in party:
                if h["name"] not in state.get("_event_fallen", []):
                    h["exp"] = int(h.get("exp", 0)) + bonus_exp
        rewards.append(
            f"\033[32m[{event['name']}]\033[0m Party healed \033[32m10% HP\033[0m,"
            f" earned \033[33m{bonus_gold}G\033[0m and \033[36m{bonus_exp} EXP\033[0m"
        )

    # ── Thieves in the Night: reward if the spawned quest was completed ────── #
    elif effect == "thieves":
        if state.get("quest_name") == "Thieves in the Night":
            coffers = int(state.get("gold", 0))
            bonus = int(coffers * 0.5)
            if bonus > 0:
                state["gold"] = coffers + bonus
                rewards.append(
                    f"\033[32m[{event['name']}]\033[0m The thieves were remanded —"
                    f" \033[33m+{bonus}G\033[0m seized from them"
                )

    # ── Read The Bones: reward line only (damage handled in apply_quest_damage) #
    elif effect == "bones":
        doomed = state.get("_bones_doomed")
        spared = state.get("_bones_spared")
        if doomed:
            rewards.append(f"\033[32m[{event['name']}]\033[0m {doomed} bore the full weight")
        if spared:
            rewards.append(f"\033[32m[{event['name']}]\033[0m {spared} passed through unscathed")

    # ── The Shaded Carriage: discount applied at recruit generation time ───── #
    # (no quest reward line needed)

    # -- For Whom The Bell Tolls: heal all roster heroes to max HP -- #
    elif effect == "bell_tolls":
        for h in state.get("roster", []):
            h["hp"] = float(h.get("max_hp", 100))
        rewards.append(f"[32m[{event['name']}][0m Every wound on the grounds has sealed — party fully healed")

    return rewards
