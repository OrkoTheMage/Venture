import datetime


def record_fallen(state: dict, fallen: list[str], roster: list[dict], quest_name: str, enemy_types: str) -> None:
    """Append fallen heroes to the graveyard in state (does not save)."""
    date_str = datetime.date.today().isoformat()
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


def build_graveyard_lines(state: dict) -> list[str]:
    """Return display lines for the graveyard."""
    graveyard = state.get("graveyard", [])
    if not graveyard:
        return ["", "  The graveyard is empty. Your heroes fight on.", ""]
    lines = ["", "  ☠  Fallen Heroes  ☠", ""]
    for entry in reversed(graveyard):
        lines.append(
            f"  {entry['name']}, {entry['class']} Lvl {entry['lvl']} — "
            f"Fell on {entry['date']} during '{entry['quest']}'"
        )
    lines.append("")
    return lines
