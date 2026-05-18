from pathlib import Path

from .state import load_state, save_state

_CARD_TPL = Path(__file__).parent / "ascii" / "classCard.txt"
_DEFAULT_ROSTER = [
    {"name": "Hadrik",  "class": "Fighter", "lvl": 1, "hp": 100, "max_hp": 100, "exp": 0},
    {"name": "Brynndar","class": "Rogue",   "lvl": 1, "hp": 75,  "max_hp": 75,  "exp": 0},
]
_BLANK = {"name": "Empty", "class": "---", "lvl": 0, "hp": 0, "max_hp": 100, "exp": 0}

ROSTER_CAP = 14


# Mirrors combat._EXP_LEVEL_THRESHOLDS — EXP required to reach levels 2-5
_EXP_THRESHOLDS = (100, 200, 400, 800)


def _filled_rows(h: dict) -> float:
    """HP fill level 0.0–5.0 in 0.5 steps."""
    try:
        hp = float(h.get("hp", 0))
        mh = float(h.get("max_hp", 100))
        if mh <= 0:
            return 0.0
        return round(max(0.0, min(1.0, hp / mh)) * 10) / 2
    except Exception:
        return 0.0


def _filled_exp_rows(h: dict) -> float:
    """EXP fill level 0.0–5.0 in 0.5 steps based on progress within current level."""
    try:
        exp = int(h.get("exp", 0))
        lvl = 1
        for t in _EXP_THRESHOLDS:
            if exp >= t:
                lvl += 1
            else:
                break
        if lvl >= len(_EXP_THRESHOLDS) + 1:  # max level — full bar
            return 5.0
        prev = _EXP_THRESHOLDS[lvl - 2] if lvl > 1 else 0
        nxt  = _EXP_THRESHOLDS[lvl - 1]
        frac = (exp - prev) / max(1, nxt - prev)
        return round(max(0.0, min(1.0, frac)) * 10) / 2
    except Exception:
        return 0.0


def _bar_fill(bar_row: int, filled: float) -> str:
    """Character pair for one bar row.

    bar_row is 0-indexed from the top (0 = top, 4 = bottom).
    filled is 0.0-5.0 in 0.5 steps.
    Returns '██' (full), '▄▄' (half, U+2584), or '  ' (empty).
    """
    if filled >= 5 - bar_row:       # fully filled
        return "██"
    if filled >= 4.5 - bar_row:     # half-filled (lower half block)
        return "▄▄"
    return "  "


def _exp_pct_to_next(h: dict) -> str:
    """Return EXP progress toward the next level as a display string.
    Shows 'MAX' at level 5, otherwise '0%'-'99%'.
    """
    try:
        exp = int(h.get("exp", 0))
        lvl = 1
        for t in _EXP_THRESHOLDS:
            if exp >= t:
                lvl += 1
            else:
                break
        if lvl >= len(_EXP_THRESHOLDS) + 1:
            return "MAX"
        prev = _EXP_THRESHOLDS[lvl - 2] if lvl > 1 else 0
        nxt  = _EXP_THRESHOLDS[lvl - 1]
        pct  = int((exp - prev) / max(1, nxt - prev) * 100)
        return f"{pct}%"
    except Exception:
        return "0%"


    text = tpl
    text = text.replace("   Hero Name   ", h0["name"].center(15), 1)
    text = text.replace("   Hero Name   ", h1["name"].center(15), 1)
    text = text.replace("   Fighter   ", h0["class"].center(13), 1)
    text = text.replace("    Rogue    ", h1["class"].center(13), 1)
    text = text.replace("    Lvl 1    ", f"Lvl {h0['lvl']}".center(13), 1)
    text = text.replace("    Lvl 1    ", f"Lvl {h1['lvl']}".center(13), 1)

    hp0,  hp1  = _filled_rows(h0),     _filled_rows(h1)
    exp0, exp1 = _filled_exp_rows(h0), _filled_exp_rows(h1)

    # Each bar row contains four ██ markers in order: HP0, EXP0, HP1, EXP1.
    # First tag every marker with a unique sentinel so sequential replacement
    # always advances (avoids re-hitting the same ██ when fill == BAR).
    BAR = "██"
    S = ("\x00A\x00", "\x00B\x00", "\x00C\x00", "\x00D\x00")  # sentinels
    result: list[str] = []
    bar_row = 0
    for line in text.splitlines():
        if BAR in line:
            # Tag each ██ with its sentinel in order
            for s in S:
                line = line.replace(BAR, s, 1)
            fills = (
                _bar_fill(bar_row, hp0),
                _bar_fill(bar_row, exp0),
                _bar_fill(bar_row, hp1),
                _bar_fill(bar_row, exp1),
            )
            for s, fill in zip(S, fills):
                line = line.replace(s, fill)
            bar_row += 1
        result.append(line)
    return result


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
        idx_w = len(str(len(roster)))  # width of largest roster index
        lines: list[str] = ["", f"Page {page + 1}/{total_pages}", ""]
        for i, h in enumerate(heroes):
            hp_pct  = int(float(h.get("hp", 100)) / max(1.0, float(h.get("max_hp", 100))) * 100)
            exp_pct = _exp_pct_to_next(h)
            name    = h["name"][:12]
            lines.append(
                f"  {start + i + 1:>{idx_w}}. \033[1m{name:<12}\033[0m"
                f"  {h['class']:<8}  Lvl {h['lvl']}  HP {hp_pct:>3}%  EXP {exp_pct:>3}"
            )
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
        print("Roster commands: rename [old name] [new name], dismiss [hero name], move [name or #] [position], list, back, quit")
        print(f"Roster cap: {ROSTER_CAP} heroes maximum.")
        return None
    if verb == "list":
        return "list"
    if verb == "rename":
        if len(parts) < 3:
            print("Usage: rename [hero name] [new name]")
            return None
        roster = state.get("roster") or []
        old_name = parts[1]
        new_name = " ".join(parts[2:])
        for h in roster:
            if h.get("name", "").lower() == old_name.lower():
                h["name"] = new_name
                save_state(state)
                print(f"Renamed {old_name} -> {new_name}")
                return "list"               
        for split in range(2, len(parts) - 0):
            candidate_old = " ".join(parts[1:split])
            candidate_new = " ".join(parts[split:])
            for h in roster:
                if h.get("name", "").lower() == candidate_old.lower():
                    h["name"] = candidate_new
                    save_state(state)
                    print(f"Renamed {candidate_old} -> {candidate_new}")
                    return "list"

        print(f"Hero '{old_name}' not found in roster.")
        return None
    if verb == "move":
        if len(parts) < 3:
            print("Usage: move [hero name or #] [position]")
            return None
        roster = state.get("roster") or []
        # Last token is the target position
        try:
            target_pos = int(parts[-1])
        except ValueError:
            print("Position must be a number.")
            return None
        if not (1 <= target_pos <= len(roster)):
            print(f"Position must be between 1 and {len(roster)}.")
            return None
        # Remaining tokens identify the hero (by index or name)
        selector = " ".join(parts[1:-1])
        hero_idx = None
        if selector.isdigit():
            n = int(selector)
            if 1 <= n <= len(roster):
                hero_idx = n - 1
        if hero_idx is None:
            for i, h in enumerate(roster):
                if h.get("name", "").lower() == selector.lower():
                    hero_idx = i
                    break
        if hero_idx is None:
            print(f"Hero '{selector}' not found in roster.")
            return None
        hero = roster.pop(hero_idx)
        roster.insert(target_pos - 1, hero)
        state["roster"] = roster
        save_state(state)
        print(f"{hero['name']} moved to position {target_pos}.")
        return "list"

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
    hp_filled  = _filled_rows(h)
    exp_filled = _filled_exp_rows(h)
    lines = [
        "┌───────────────┐",
        f"│{name}│",
        "├───────────────┤",
        "│HP           XP│",
    ]
    for i in range(5):
        hp_fill  = _bar_fill(i, hp_filled)
        exp_fill = _bar_fill(i, exp_filled)
        lines.append(f"│{hp_fill}           {exp_fill}│")
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
                price = " FREE"
            else:
                price = f"{o['price']:>4}G"
            name = o["name"][:12]
            out.append(
                f"  {i + 1}. \033[1m{name:<12}\033[0m"
                f"  {o['class']:<8}  Lvl {o['lvl']}  HP {hp_pct:>3}%  {price}"
            )
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
