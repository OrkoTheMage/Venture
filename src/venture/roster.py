from pathlib import Path

from .state import load_state, save_state

_CARD_TPL = Path(__file__).parent / "ascii" / "classCard.txt"
_DEFAULT_ROSTER = [
    {"name": "Hadrik",  "class": "Fighter", "lvl": 1, "hp": 100, "max_hp": 100, "exp": 0},
    {"name": "Brynndar","class": "Rogue",   "lvl": 1, "hp": 75,  "max_hp": 75,  "exp": 0},
]
_BLANK = {"name": "Empty", "class": "---", "lvl": 0, "hp": 0, "max_hp": 100, "exp": 0}

ROSTER_CAP = 14


def _filled_rows(h: dict) -> int:
    try:
        hp = float(h.get("hp", 0))
        mh = float(h.get("max_hp", 100))
        return int(round(max(0.0, min(1.0, hp / mh)) * 5)) if mh > 0 else 0
    except Exception:
        return 0


def _render_pair(tpl: str, h0: dict, h1: dict) -> list[str]:
    text = tpl
    text = text.replace("   Hero Name   ", h0["name"].center(15), 1)
    text = text.replace("   Hero Name   ", h1["name"].center(15), 1)
    text = text.replace("   Fighter   ", h0["class"].center(13), 1)
    text = text.replace("    Rogue    ", h1["class"].center(13), 1)
    text = text.replace("    Lvl 1    ", f"Lvl {h0['lvl']}".center(13), 1)
    text = text.replace("    Lvl 1    ", f"Lvl {h1['lvl']}".center(13), 1)
    BAR, EMPTY, KEEP = "             ██", "               ", "\x00K\x00"
    f0, f1 = _filled_rows(h0), _filled_rows(h1)
    for row in range(5):
        for fv in (f0, f1):
            text = text.replace(BAR, KEEP if row >= (5 - fv) else EMPTY, 1)
    return text.replace(KEEP, BAR).splitlines()


_CARDS_PER_PAGE = 4


def get_roster_page_count(state: dict) -> int:
    """Return the total number of roster pages (4 heroes per page)."""
    import math
    roster = state.get("roster") or []
    return max(1, math.ceil(len(roster) / _CARDS_PER_PAGE))


def build_roster_lines(state: dict, page: int = 0, compact: bool = False) -> list[str]:
    """Return all lines needed to display one page of the roster (up to 4 cards)."""
    roster = state.get("roster") or []
    if not roster:
        return ["No heroes in roster."]

    total_pages = get_roster_page_count(state)
    page = max(0, min(page, total_pages - 1))
    start = page * _CARDS_PER_PAGE
    heroes = roster[start : start + _CARDS_PER_PAGE]

    if compact:
        lines: list[str] = ["", f"Page {page + 1}/{total_pages}", ""]
        for i, h in enumerate(heroes):
            hp_pct = int(float(h.get("hp", 100)) / max(1.0, float(h.get("max_hp", 100))) * 100)
            lines.append(f"  {start + i + 1}. \033[1m{h['name']}\033[0m  {h['class']}  Lvl {h['lvl']}  HP {hp_pct}%")
        lines += ["", f"  Heroes: {len(roster)}/{ROSTER_CAP}"]
        return lines

    cards = [_single_card_lines(h) for h in heroes]

    # Card area width: 2-space indent + cards (17 each) + 3-space gaps
    card_area_width = 2 + len(cards) * 17 + (len(cards) - 1) * 3

    page_indicator = f"Page {page + 1}/{total_pages}"
    lines = ["", page_indicator.center(card_area_width), ""]
    for row_parts in zip(*cards):
        lines.append("  " + "   ".join(row_parts))

    lines.append("")
    lines.append(f"  Heroes: {len(roster)}/{ROSTER_CAP}")
    return lines


def ensure_default_roster(state: dict) -> None:
    """Populate state with the default starting roster if it has never been seeded."""
    if not state.get("roster_seeded"):
        import copy
        state["roster"] = copy.deepcopy(_DEFAULT_ROSTER)
        state["roster_seeded"] = True
        save_state(state)


def handle_roster_command(verb: str, parts: list[str], state: dict) -> str | None:
    """Process a single roster sub-command.

    Returns:
        'quit'  — caller should exit the game
        'back'  — caller should leave roster mode
        None    — command handled; continue roster loop
    """
    if not verb or verb in ("back", "done"):
        return "back"
    if verb in ("quit", "exit"):
        return "quit"
    if verb == "help":
        print("Roster commands: rename [old name] [new name], dismiss [hero name], list, back, quit")
        print(f"Roster cap: {ROSTER_CAP} heroes maximum.")
        return None
    if verb == "list":
        return "list"
    if verb == "rename":
        if len(parts) < 3:
            print("Usage: rename [hero name] [new name]")
            return None
        old_name = parts[1]
        new_name = " ".join(parts[2:])
        roster = state.get("roster") or []
        for h in roster:
            if h.get("name", "").lower() == old_name.lower():
                h["name"] = new_name
                save_state(state)
                print(f"Renamed {old_name} -> {new_name}")
                return "list"
        print(f"Hero '{old_name}' not found in roster.")
        return None
    if verb == "dismiss":
        if len(parts) < 2:
            print("Usage: dismiss [hero name]")
            return None
        target = " ".join(parts[1:])
        roster = state.get("roster") or []
        party_names = state.get("quest_party") or []
        for i, h in enumerate(roster):
            if h.get("name", "").lower() == target.lower():
                if state.get("quest_start") and h["name"] in party_names:
                    print(f"{h['name']} is currently on a quest and cannot be dismissed.")
                    return None
                if len(roster) <= 4:
                    print("Cannot dismiss: roster must have at least 4 heroes.")
                    return None
                removed = roster.pop(i)
                state["roster"] = roster
                dismissed = state.get("dismissed") or []
                dismissed.append(removed)
                state["dismissed"] = dismissed
                save_state(state)
                print(f"{removed['name']} the {removed['class']} has been dismissed.")
                return "list"
        print(f"Hero '{target}' not found in roster.")
        return None
    print("Unknown roster command. Type 'help'.")
    return None


# ── Recruit card rendering ─────────────────────────────────────────────────── #

def _single_card_lines(h: dict) -> list[str]:
    """Build lines for one class card, 17 chars wide."""
    name = f"\033[1m{h['name'].center(15)}\033[0m"
    cls  = h["class"].center(13)
    lvl  = f"Lvl {h['lvl']}".center(13)
    filled = _filled_rows(h)
    lines = [
        "┌───────────────┐",
        f"│{name}│",
        "├───────────────┤",
        "│             HP│",
    ]
    for i in range(5):
        lines.append("│             ██│" if i >= (5 - filled) else "│               │")
    lines += [
        "├───────────────┤",
        "│┌─────────────┐│",
        f"││{cls}││",
        f"││{lvl}││",
        "│└─────────────┘│",
        "└───────────────┘",
    ]
    return lines  # 15 lines, each 17 chars wide


def build_recruit_card_lines(offers: list[dict], compact: bool = False) -> list[str]:
    """Return display lines for up to 3 recruit offer cards with price labels."""
    if not offers:
        return ["No recruits available."]

    if compact:
        out: list[str] = ["", " Recruits available — refreshes after each quest:", ""]
        for i, o in enumerate(offers):
            hp_pct = int(float(o.get("hp", 100)) / max(1.0, float(o.get("max_hp", 100))) * 100)
            if o.get("hired"):
                price = "HIRED"
            elif o["price"] == 0:
                price = "FREE"
            else:
                price = f"{o['price']}G"
            out.append(f"  {i + 1}. \033[1m{o['name']}\033[0m  {o['class']}  Lvl {o['lvl']}  HP {hp_pct}%  {price}")
        return out

    cards = [_single_card_lines(h) for h in offers]
    price_labels = []
    for i, o in enumerate(offers):
        if o.get("hired"):
            price_labels.append("--- HIRED ---")
        elif o["price"] == 0:
            price_labels.append(f"{i + 1}.    FREE")
        else:
            price_labels.append(f"{i + 1}.   {o['price']}G")

    out: list[str] = ["", " Recruits available — refreshes after each quest:", ""]
    for row_parts in zip(*cards):
        out.append("  " + "   ".join(row_parts))
    out.append("  " + "   ".join(lbl.center(17) for lbl in price_labels))
    out += [""]
    return out
