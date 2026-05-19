from __future__ import annotations
import random
from ..utils.state import save_state
from .combat import max_hp_for
from .heroes import ROSTER_CAP
from .events import get_active_event


# ── Name / level pools ──────────────────────────────────────────────────── #
_RECRUIT_NAMES = [
    "Aldric", "Brenna", "Corvus", "Dara", "Edwyn", "Fiona", "Gareth",
    "Hilda", "Ivar", "Jessa", "Karim", "Mord", "Nira", "Oswin",
    "Petra", "Rook", "Sera", "Thorn", "Una", "Vex", "Wren",
    "Bran", "Cael", "Dwyn", "Elke", "Finn", "Gwynn", "Holt",
    "Idris", "Joryn", "Keld", "Lyra", "Maren", "Noel", "Orin",
]

_RECRUIT_LEVEL_EXP = {1: 0, 2: 100, 3: 200, 4: 400, 5: 800}


# ── Offer generation ────────────────────────────────────────────────────── #

# Return the 3 recruit offers, generating and caching them if not yet set.
def build_recruit_offers(state: dict) -> list[dict]:
    if state.get("recruit_offers"):
        return state["recruit_offers"]

    classes = ["Fighter", "Rogue", "Wizard", "Cleric"]
    roster = state.get("roster") or []
    orig_roster_count = len(roster)

    # Decide how many offers to generate (normally 3, but 4 when roster is 0)
    num_offers = 4 if orig_roster_count == 0 else 3

    existing_names = {h["name"].lower() for h in roster}
    available_names = [n for n in _RECRUIT_NAMES if n.lower() not in existing_names]
    if len(available_names) < num_offers:
        available_names = _RECRUIT_NAMES[:]
    chosen_names = random.sample(available_names, num_offers)
    chosen_classes = random.sample(classes, num_offers)

    # Determine levels and prices based on current roster size per rules:
    # roster >=4 or roster ==3:  [(1,0), (2,300), (3,500)]
    # roster ==2:                 [(1,0), (1,0), (2,300)]
    # roster ==1:                 [(1,0), (1,0), (1,0)]
    # roster ==0:                 four offers all (1,0)
    if orig_roster_count >= 3:
        template = [ (1, 0), (2, 300), (3, 500) ]
    elif orig_roster_count == 2:
        template = [ (1, 0), (1, 0), (2, 300) ]
    elif orig_roster_count == 1:
        template = [ (1, 0), (1, 0), (1, 0) ]
    else:  # orig_roster_count == 0
        template = [ (1, 0), (1, 0), (1, 0), (1, 0) ]

    offers: list[dict] = []
    for (name, cls), (lvl, price) in zip(zip(chosen_names, chosen_classes), template):
        hp = float(max_hp_for(cls, lvl))
        offers.append({
            "name": name, "class": cls, "lvl": lvl,
            "price": price, "hp": hp, "max_hp": hp,
            "hired": False,
        })

    state["recruit_offers"] = offers
    save_state(state)

    # Apply Shaded Carriage discount if active (slot 2 free, slot 3 50% off)
    if get_active_event(0, state).get("effect") == "carriage":
        if len(offers) > 1:
            offers[1]["price"] = 0
        if len(offers) > 2:
            offers[2]["price"] = offers[2]["price"] // 2
        state["recruit_offers"] = offers
        save_state(state)

    # Apply Returned Banner-Man if active event (4th slot, level 5, free)
    if get_active_event(0, state).get("effect") == "banner_man":
        existing_names = {o["name"].lower() for o in offers}
        available_names = [n for n in _RECRUIT_NAMES if n.lower() not in existing_names]
        if available_names:
            name = random.choice(available_names)
            cls  = random.choice(["Fighter", "Rogue", "Wizard", "Cleric"])
            hp   = float(max_hp_for(cls, 5))
            offers.append({
                "name": name, "class": cls, "lvl": 5,
                "price": 0, "hp": hp, "max_hp": hp, "exp": 800,
                "hired": False, "banner_man": True,
            })
            state["recruit_offers"] = offers
            save_state(state)

    return offers


# ── Hiring ───────────────────────────────────────────────────────────────── #

# Hire the recruit at position idx (0-based). Returns (success, message).
def hire_recruit(state: dict, idx: int) -> tuple[bool, str]:
    roster = state.get("roster", [])
    if len(roster) >= ROSTER_CAP:
        return False, f"Roster is full ({ROSTER_CAP}/{ROSTER_CAP}). Dismiss a hero before recruiting."
    offers = state.get("recruit_offers", [])
    if not (0 <= idx < len(offers)):
        return False, "Invalid selection."
    offer = offers[idx]
    if offer.get("hired"):
        return False, f"{offer['name']} has already been hired."
    price = offer["price"]
    gold = int(state.get("gold", 0))
    if gold < price:
        return False, f"Not enough gold. Need {price}G, have {gold}G."

    exp = _RECRUIT_LEVEL_EXP.get(offer["lvl"], 0)
    hp = float(max_hp_for(offer["class"], offer["lvl"]))
    hero = {
        "name": offer["name"],
        "class": offer["class"],
        "lvl": offer["lvl"],
        "hp": hp,
        "max_hp": hp,
        "exp": exp,
    }
    state["gold"] = gold - price
    state["roster"] = state.get("roster", []) + [hero]
    offers[idx]["hired"] = True
    state["recruit_offers"] = offers
    save_state(state)
    cost_str = "FREE" if price == 0 else f"{price}G"
    return True, f"{hero['name']} the {hero['class']} (Lvl {hero['lvl']}) joins your roster! [{cost_str}]"
