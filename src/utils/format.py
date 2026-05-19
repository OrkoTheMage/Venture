from __future__ import annotations

import textwrap


# ── Duration formatting ───────────────────────────────────────────────────── #

# Format a seconds value as a human-readable duration string (e.g. "2m 30s").
def format_duration(seconds: float | int) -> str:
    try:
        total = int(max(0, float(seconds)))
    except Exception:
        total = 0
    mins, secs = divmod(total, 60)
    return f"{mins}m {secs}s"


# ── Lore text rendering ───────────────────────────────────────────────────── #

# Return display lines for a lore entry. The bold ending is rendered bold.
def render_lore(lore: tuple[str, str] | str, width: int, indent: str = "  ") -> list[str]:
    if isinstance(lore, str):
        return [f"{indent}{ln}" for ln in textwrap.wrap(lore, width=max(20, width))]
    body, bold = lore
    if body and bold:
        combined = body.rstrip() + " \033[1m" + bold.strip() + "\033[0m"
        return [f"{indent}{ln}" for ln in textwrap.wrap(combined, width=max(20, width))]
    if body:
        return [f"{indent}{ln}" for ln in textwrap.wrap(body, width=max(20, width))]
    if bold:
        return [f"{indent}\033[1m{ln}\033[0m" for ln in textwrap.wrap(bold, width=max(20, width))]
    return []

# Return the number of wrapped display lines for a lore entry.
def lore_line_count(lore: tuple[str, str] | str, width: int) -> int:
    return len(render_lore(lore, width, indent=""))
