from __future__ import annotations

import datetime


# ── Record ────────────────────────────────────────────────────────────────── #

# Append fallen heroes to the graveyard in state (does not save).
def record_fallen(
    state: dict,
    fallen: list[str],
    roster: list[dict],
    quest_name: str,
    enemy_types: str,
) -> None:
    date_str  = datetime.date.today().isoformat()
    graveyard = state.get("graveyard", [])
    for h in roster:
        if h["name"] in fallen:
            graveyard.append({
                "name":    h["name"],
                "class":   h.get("class", "Unknown"),
                "lvl":     h.get("lvl", 1),
                "date":    date_str,
                "quest":   quest_name,
                "enemies": enemy_types,
            })
    state["graveyard"] = graveyard
