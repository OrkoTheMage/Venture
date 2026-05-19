from __future__ import annotations

from ..logic.progress import get_journal_entries


# ── Display ───────────────────────────────────────────────────────────────── #

# Return display lines for the journal screen.
def build_journal_lines(state: dict, compact: bool = False) -> list[str]:
    entries    = get_journal_entries(state)
    done_count = sum(1 for e in entries if e["done"])
    total      = len(entries)

    if compact:
        lines: list[str] = [
            "",
            f"  \033[1mJournal\033[0m  ({done_count}/{total} complete)",
            "",
        ]
        for entry in entries:
            box = "[\033[1;32mX\033[0m]" if entry["done"] else "[ ]"
            lines.append(f"  {box}  {entry['label']}")
        lines.append("")
        return lines

    # Regular: titled header with separator and progress line
    lines = [
        "",
        "  \033[1mJournal — Estate Progress\033[0m",
        "  " + "─" * 40,
        "",
        f"  Progress: {done_count} / {total} goals complete",
        "",
    ]
    for entry in entries:
        box = "[\033[1;32mX\033[0m]" if entry["done"] else "[ ]"
        lines.append(f"  {box}  {entry['label']}")
    lines.append("")
    return lines
