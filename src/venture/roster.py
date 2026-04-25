from pathlib import Path

from .state import load_state, save_state

_CARD_TPL = Path(__file__).parent / "ascii" / "classCard.txt"
_DEFAULT_ROSTER = [
    {"name": "Hadrik",  "class": "Fighter", "lvl": 1, "hp": 100, "max_hp": 100, "exp": 0},
    {"name": "Brynndar","class": "Rogue",   "lvl": 1, "hp": 75,  "max_hp": 75,  "exp": 0},
]
_BLANK = {"name": "Empty", "class": "---", "lvl": 0, "hp": 0, "max_hp": 100, "exp": 0}


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


def build_roster_lines(state: dict) -> list[str]:
    """Return all lines needed to display the full roster as paired cards."""
    roster = state.get("roster") or []
    if not roster:
        return ["No heroes in roster."]
    try:
        tpl = _CARD_TPL.read_text()
    except Exception:
        return [f"{h['name']} | {h['class']} | Lvl {h['lvl']}" for h in roster]

    all_lines: list[str] = []
    for i in range(0, len(roster), 2):
        h0 = roster[i]
        h1 = roster[i + 1] if i + 1 < len(roster) else _BLANK
        all_lines.extend(_render_pair(tpl, h0, h1))
    return all_lines


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
        print("Roster commands: rename [old name] [new name], list, back, quit")
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
    print("Unknown roster command. Type 'help'.")
    return None
