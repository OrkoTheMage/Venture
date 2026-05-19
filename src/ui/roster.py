from __future__ import annotations

from .cards import _single_card_lines, _exp_pct_to_next
from ..logic.heroes import get_roster_page_count, _CARDS_PER_PAGE


# ── Display ───────────────────────────────────────────────────────────────── #

# Return all lines needed to display one page of the roster (up to 4 cards).
def build_roster_lines(state: dict, page: int = 0, compact: bool = False) -> list[str]:
    roster = state.get("roster") or []
    if not roster:
        return ["No heroes in roster."]

    total_pages = get_roster_page_count(state)
    page        = max(0, min(page, total_pages - 1))
    start       = page * _CARDS_PER_PAGE
    heroes      = roster[start : start + _CARDS_PER_PAGE]

    from ..logic.heroes import ROSTER_CAP

    if compact:
        idx_w  = len(str(len(roster)))
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

    card_area_width = 2 + len(cards) * 17 + (len(cards) - 1) * 3
    page_indicator  = f"Page {page + 1}/{total_pages}"
    lines = ["", page_indicator.center(card_area_width), ""]
    for row_parts in zip(*cards):
        lines.append("  " + "   ".join(row_parts))

    lines.append("")
    lines.append(f"  Heroes: {len(roster)}/{ROSTER_CAP}")
    return lines
