from __future__ import annotations

import math

from ..utils.state import load_state, save_state


# ── Constants ─────────────────────────────────────────────────────────────── #

_DEFAULT_ROSTER = [
    {"name": "Hadrik",   "class": "Fighter", "lvl": 1, "hp": 100, "max_hp": 100, "exp": 0},
    {"name": "Brynndar", "class": "Rogue",   "lvl": 1, "hp": 75,  "max_hp": 75,  "exp": 0},
]

ROSTER_CAP      = 14
_CARDS_PER_PAGE = 4


# ── Roster data ───────────────────────────────────────────────────────────── #

# Populate state with the default starting roster if it has never been seeded.
def ensure_default_roster(state: dict) -> None:
    if not state.get("roster_seeded"):
        import copy
        state["roster"] = copy.deepcopy(_DEFAULT_ROSTER)
        state["roster_seeded"] = True
        save_state(state)

# Return the total number of roster pages (4 heroes per page).
def get_roster_page_count(state: dict) -> int:
    roster = state.get("roster") or []
    return max(1, math.ceil(len(roster) / _CARDS_PER_PAGE))


# ── Roster commands ───────────────────────────────────────────────────────── #

# Process a single roster sub-command.
# Returns: 'quit' to exit the game, 'back' to leave roster mode,
#          'list' to redraw, None to continue.
def handle_roster_command(verb: str, parts: list[str], state: dict) -> tuple[str | None, str]:
    if not verb or verb in ("back", "done"):
        return "back", ""
    if verb in ("quit", "exit"):
        return "quit", ""
    if verb == "help":
        return None, (
            "\033[1mrename\033[0m [old] [new]  │  "
            "\033[1mdismiss\033[0m [name]  │  "
            "\033[1mmove\033[0m [name/#] [pos]  │  "
            f"\033[1mcap:\033[0m {ROSTER_CAP}"
        )
    if verb == "rename":
        if len(parts) < 3:
            return None, "Usage: rename [hero name] [new name]"
        roster   = state.get("roster") or []
        old_name = parts[1]
        new_name = " ".join(parts[2:])
        for h in roster:
            if h.get("name", "").lower() == old_name.lower():
                h["name"] = new_name
                save_state(state)
                return "list", f"Renamed {old_name} \u2192 {new_name}"
        for split in range(2, len(parts) - 0):
            candidate_old = " ".join(parts[1:split])
            candidate_new = " ".join(parts[split:])
            for h in roster:
                if h.get("name", "").lower() == candidate_old.lower():
                    h["name"] = candidate_new
                    save_state(state)
                    return "list", f"Renamed {candidate_old} \u2192 {candidate_new}"
        return None, f"Hero '{old_name}' not found in roster."
    if verb == "move":
        if len(parts) < 3:
            return None, "Usage: move [hero name or #] [position]"
        roster = state.get("roster") or []
        try:
            target_pos = int(parts[-1])
        except ValueError:
            return None, "Position must be a number."
        if not (1 <= target_pos <= len(roster)):
            return None, f"Position must be between 1 and {len(roster)}."
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
            return None, f"Hero '{selector}' not found in roster."
        hero = roster.pop(hero_idx)
        roster.insert(target_pos - 1, hero)
        state["roster"] = roster
        save_state(state)
        return "list", f"{hero['name']} moved to position {target_pos}."
    if verb == "dismiss":
        if len(parts) < 2:
            return None, "Usage: dismiss [hero name]"
        target      = " ".join(parts[1:])
        roster      = state.get("roster") or []
        party_names = state.get("quest_party") or []
        for i, h in enumerate(roster):
            if h.get("name", "").lower() == target.lower():
                if state.get("quest_start") and h["name"] in party_names:
                    return None, f"{h['name']} is currently on a quest and cannot be dismissed."
                if len(roster) <= 4:
                    return None, "Cannot dismiss: roster must have at least 4 heroes."
                removed   = roster.pop(i)
                state["roster"] = roster
                dismissed = state.get("dismissed") or []
                dismissed.append(removed)
                state["dismissed"] = dismissed
                save_state(state)
                return "list", f"{removed['name']} the {removed['class']} has been dismissed."
        return None, f"Hero '{target}' not found in roster."
    return None, "Unknown roster command: Type 'help'."
