import random

from .state import save_state
from .combat import max_hp_for
from .roster import ROSTER_CAP

_RECRUIT_NAMES = [
    "Aldric", "Brenna", "Corvus", "Dara", "Edwyn", "Fiona", "Gareth",
    "Hilda", "Ivar", "Jessa", "Karim", "Mord", "Nira", "Oswin",
    "Petra", "Rook", "Sera", "Thorn", "Una", "Vex", "Wren",
    "Bran", "Cael", "Dwyn", "Elke", "Finn", "Gwynn", "Holt",
    "Idris", "Joryn", "Keld", "Lyra", "Maren", "Noel", "Orin",
]

_RECRUIT_LEVEL_EXP = {1: 0, 2: 100, 3: 200}


def build_recruit_offers(state: dict) -> list[dict]:
    """Return the 3 recruit offers, generating and caching them if not yet set."""
    if state.get("recruit_offers"):
        return state["recruit_offers"]

    classes = ["Fighter", "Rogue", "Wizard", "Cleric"]
    existing_names = {h["name"].lower() for h in state.get("roster", [])}
    available_names = [n for n in _RECRUIT_NAMES if n.lower() not in existing_names]
    if len(available_names) < 3:
        available_names = _RECRUIT_NAMES[:]
    chosen_names = random.sample(available_names, 3)
    chosen_classes = random.sample(classes, 3)

    offers: list[dict] = []
    for i, (name, cls, lvl, price) in enumerate([
        (chosen_names[0], chosen_classes[0], 1, 0),
        (chosen_names[1], chosen_classes[1], 2, 300),
        (chosen_names[2], chosen_classes[2], 3, 500),
    ]):
        hp = float(max_hp_for(cls, lvl))
        offers.append({
            "name": name, "class": cls, "lvl": lvl,
            "price": price, "hp": hp, "max_hp": hp,
            "hired": False,
        })

    state["recruit_offers"] = offers
    save_state(state)
    return offers


def hire_recruit(state: dict, idx: int) -> tuple[bool, str]:
    """Hire the recruit at position idx (0-based). Returns (success, message)."""
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
