"""Journal — tracks player progress and goals."""


def _any_hero_at_class_and_lvl(state: dict, hero_class: str, min_lvl: int) -> bool:
    """Return True if any hero in roster, graveyard, or dismissed list matches class and level."""
    all_heroes = (
        list(state.get("roster", []))
        + list(state.get("graveyard", []))
        + list(state.get("dismissed", []))
    )
    return any(
        h.get("class") == hero_class and int(h.get("lvl", 1)) >= min_lvl
        for h in all_heroes
    )


def get_journal_entries(state: dict) -> list[dict]:
    """Return a list of journal entry dicts with 'label' and 'done' keys."""
    roster    = list(state.get("roster", []))
    graveyard = list(state.get("graveyard", []))
    dismissed = list(state.get("dismissed", []))
    all_heroes = roster + graveyard + dismissed
    items = state.get("items", [])

    has_lvl3 = state.get("has_had_lvl3") or any(
        int(h.get("lvl", 1)) >= 3 for h in all_heroes
    )
    has_lvl5 = state.get("has_had_lvl5") or any(
        int(h.get("lvl", 1)) >= 5 for h in all_heroes
    )

    return [
        {
            "label": "Have a hero achieve LVL 3",
            "done": bool(has_lvl3),
        },
        {
            "label": "Have a hero achieve LVL 5",
            "done": bool(has_lvl5),
        },
        {
            "label": "Have a Fighter achieve LVL 5",
            "done": _any_hero_at_class_and_lvl(state, "Fighter", 5),
        },
        {
            "label": "Have a Rogue achieve LVL 5",
            "done": _any_hero_at_class_and_lvl(state, "Rogue", 5),
        },
        {
            "label": "Have a Wizard achieve LVL 5",
            "done": _any_hero_at_class_and_lvl(state, "Wizard", 5),
        },
        {
            "label": "Have a Cleric achieve LVL 5",
            "done": _any_hero_at_class_and_lvl(state, "Cleric", 5),
        },
        {
            "label": "Acquire the Signet Ring",
            "done": "Signet Ring" in items,
        },
        {
            "label": "Acquire the Ancestral Skull",
            "done": "Ancestral Skull" in items,
        },
    ]


def build_journal_lines(state: dict) -> list[str]:
    """Return display lines for the journal screen."""
    entries = get_journal_entries(state)
    done_count = sum(1 for e in entries if e["done"])
    total = len(entries)

    lines: list[str] = [
        "",
        "  \033[1mJournal\033[0m",
        "",
        f"  Progress: {done_count}/{total}",
        "",
    ]
    for entry in entries:
        box = "[x]" if entry["done"] else "[ ]"
        lines.append(f"  {box}  {entry['label']}")
    lines.append("")
    return lines
