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


def build_graveyard_lines(state: dict, compact: bool = False) -> list[str]:
    """Return display lines for the graveyard."""
    graveyard = state.get("graveyard", [])
    if not graveyard:
        return ["", "  The graveyard is empty. Your heroes fight on.", ""]

    entries = list(reversed(graveyard))  # most recent first

    if compact:
        n = len(entries)
        lines = ["", f"  \033[1mFallen Heroes\033[0m  ({n} fallen)", ""]
        for e in entries:
            name = e["name"][:12]
            lines.append(
                f"  \033[1m{name:<12}\033[0m"
                f"  {e['class']:<8}  Lvl {e['lvl']}"
                f"  {e['date']}  {e['quest']}"
            )
        lines.append("")
        return lines

    # Regular: one block per hero with name/class header and indented details
    lines = ["", "  \033[1mFallen Heroes\033[0m", "  " + "\u2500" * 40, ""]
    for e in entries:
        lines.append(
            f"  \033[1m{e['name']}\033[0m"
            f"  --  {e['class']}  --  Lvl {e['lvl']}"
        )
        lines.append(f"     Fell on {e['date']} during '{e['quest']}'")
        lines.append(f"     Enemies: {e['enemies']}")
        lines.append("")
    return lines
