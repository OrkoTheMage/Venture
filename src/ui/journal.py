from __future__ import annotations

from ..logic.progress import get_journal_entries
from ..logic.questDefinitions import LOCATION_QUESTS


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _box(done: bool) -> str:
    # Return a checkbox string for done/not-done.
    return "[\033[1;32mX\033[0m]" if done else "[ ]"


def _location_clear_lines(state: dict, compact: bool = False) -> list[str]:
    # Return the lines for the separate Location Clears / Quest Activity block.

    lc = state.get("location_clears", {})
    locations = list(LOCATION_QUESTS.keys())

    lines: list[str] = []
    if compact:
        lines.append("  \033[1mQuest Activity\033[0m")
        for loc in locations:
            clears = int(lc.get(loc, 0))
            lines.append(f"    {loc}: {clears}")
        lines.append("")
        return lines

    lines.append("  \033[1mLocation Clears\033[0m")
    for loc in locations:
        clears = int(lc.get(loc, 0))
        lines.append(f"    {loc}: {clears}/5 clears")
    lines.append("")
    return lines


# ── Display ───────────────────────────────────────────────────────────────── #


def build_journal_lines(state: dict, compact: bool = False) -> list[str]:
    # Return display lines for the journal screen.
    entries = get_journal_entries(state)
    done_count = sum(1 for e in entries if e["done"]) if entries else 0
    total = len(entries)

    if compact:
        lines: list[str] = ["", f"  \033[1mJournal\033[0m  ({done_count}/{total} complete)", ""]
        lines += _location_clear_lines(state, compact=True)
        for entry in entries:
            lines.append(f"  {_box(entry['done'])}  {entry['label']}")
        lines.append("")
        return lines

    # Regular (expanded) view
    lines = ["", "  \033[1mJournal — Estate Progress\033[0m", "  " + "─" * 40, "", f"  Progress: {done_count} / {total} goals complete", ""]
    lines += _location_clear_lines(state, compact=False)
    for entry in entries:
        lines.append(f"  {_box(entry['done'])}  {entry['label']}")
    lines.append("")
    return lines
