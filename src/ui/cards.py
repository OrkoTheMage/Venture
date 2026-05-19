from __future__ import annotations
from pathlib import Path
from ..logic.spells import get_available_spells

_QUEST_CARD_TPL = Path(__file__).parent.parent / "ascii" / "questCard.txt"
_SPELL_CARD_TPL = Path(__file__).parent.parent / "ascii" / "spellCard.txt"


# ── EXP / bar helpers ─────────────────────────────────────────────────────── #

# Mirrors combat._EXP_LEVEL_THRESHOLDS — EXP required to reach levels 2-5.
_EXP_THRESHOLDS = (100, 200, 400, 800)

# HP fill level 0.0–5.0 in 0.5 steps.
def _filled_rows(h: dict) -> float:
    try:
        hp = float(h.get("hp", 0))
        mh = float(h.get("max_hp", 100))
        if mh <= 0:
            return 0.0
        return round(max(0.0, min(1.0, hp / mh)) * 10) / 2
    except Exception:
        return 0.0

# EXP fill level 0.0–5.0 in 0.5 steps based on progress within current level.
def _filled_exp_rows(h: dict) -> float:
    try:
        exp = int(h.get("exp", 0))
        lvl = 1
        for t in _EXP_THRESHOLDS:
            if exp >= t:
                lvl += 1
            else:
                break
        if lvl >= len(_EXP_THRESHOLDS) + 1:  # max level — full bar
            return 5.0
        prev = _EXP_THRESHOLDS[lvl - 2] if lvl > 1 else 0
        nxt  = _EXP_THRESHOLDS[lvl - 1]
        frac = (exp - prev) / max(1, nxt - prev)
        return round(max(0.0, min(1.0, frac)) * 10) / 2
    except Exception:
        return 0.0

# Character pair for one bar row.
# bar_row is 0-indexed from the top (0 = top, 4 = bottom).
# filled is 0.0-5.0 in 0.5 steps.
# Returns '██' (full), '▄▄' (half, U+2584), or '  ' (empty).
def _bar_fill(bar_row: int, filled: float) -> str:
    if filled >= 5 - bar_row:       # fully filled
        return "██"
    if filled >= 4.5 - bar_row:     # half-filled (lower half block)
        return "▄▄"
    return "  "

# Return EXP progress toward the next level as a display string.
# Shows 'MAX' at level 5, otherwise '0%'-'99%'.
def _exp_pct_to_next(h: dict) -> str:
    try:
        exp = int(h.get("exp", 0))
        lvl = 1
        for t in _EXP_THRESHOLDS:
            if exp >= t:
                lvl += 1
            else:
                break
        if lvl >= len(_EXP_THRESHOLDS) + 1:
            return "MAX"
        prev = _EXP_THRESHOLDS[lvl - 2] if lvl > 1 else 0
        nxt  = _EXP_THRESHOLDS[lvl - 1]
        pct  = int((exp - prev) / max(1, nxt - prev) * 100)
        return f"{pct}%"
    except Exception:
        return "0%"


# ── Class / hero card ─────────────────────────────────────────────────────── #

# Build lines for one class card, 17 chars wide.
def _single_card_lines(h: dict) -> list[str]:
    name       = f"\033[1m{h['name'].center(15)}\033[0m"
    cls        = h["class"].center(13)
    lvl        = f"Lvl {h['lvl']}".center(13)
    hp_filled  = _filled_rows(h)
    exp_filled = _filled_exp_rows(h)
    lines = [
        "┌───────────────┐",
        f"│{name}│",
        "├───────────────┤",
        "│HP           XP│",
    ]
    for i in range(5):
        hp_fill  = _bar_fill(i, hp_filled)
        exp_fill = _bar_fill(i, exp_filled)
        lines.append(f"│{hp_fill}           {exp_fill}│")
    lines += [
        "├───────────────┤",
        "│┌─────────────┐│",
        f"││{cls}││",
        f"││{lvl}││",
        "│└─────────────┘│",
        "└───────────────┘",
    ]
    return lines  # 15 lines, each 17 chars wide


# ── Recruit card display ──────────────────────────────────────────────────── #

# Return display lines for up to 3 recruit offer cards with price labels.
def build_recruit_card_lines(offers: list[dict], compact: bool = False) -> list[str]:
    if not offers:
        return ["No recruits available."]

    if compact:
        out: list[str] = ["", " Recruits available — refreshes after each quest:", ""]
        for i, o in enumerate(offers):
            hp_pct = int(float(o.get("hp", 100)) / max(1.0, float(o.get("max_hp", 100))) * 100)
            if o.get("hired"):
                price = "HIRED"
            elif o["price"] == 0:
                price = " FREE"
            else:
                price = f"{o['price']:>4}G"
            name = o["name"][:12]
            out.append(
                f"  {i + 1}. \033[1m{name:<12}\033[0m"
                f"  {o['class']:<8}  Lvl {o['lvl']}  HP {hp_pct:>3}%  {price}"
            )
        return out

    cards        = [_single_card_lines(h) for h in offers]
    price_labels = []
    for i, o in enumerate(offers):
        if o.get("hired"):
            price_labels.append("--- HIRED ---")
        elif o["price"] == 0:
            price_labels.append(f"{i + 1}.    FREE")
        else:
            price_labels.append(f"{i + 1}.   {o['price']}G")

    out: list[str] = ["", " Recruits available — refreshes after each quest:", ""]
    for row_parts in zip(*cards):
        out.append("  " + "   ".join(row_parts))
    out.append("  " + "   ".join(lbl.center(17) for lbl in price_labels))
    out += [""]
    return out


# ── Quest card rendering ──────────────────────────────────────────────────── #

# Substitute quest data into one quest card template.
def _render_quest_card(tpl: str, q: dict) -> str:
    lines_tpl = tpl.splitlines()
    out: list[str] = []
    for line in lines_tpl:
        if "Quest Name" in line:
            l = line.find("│")
            r = line.rfind("│")
            if l != -1 and r != -1 and r > l:
                line = line[: l + 1] + f"\033[1m{q['name'].center(r - l - 1)}\033[0m" + line[r:]
        elif "Danger Level" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + f"Danger Level: {q['danger']}".center(r - l) + line[r:]
        elif "Quest Length" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + f"Quest Length: {q['length']}".center(r - l) + line[r:]
        elif "Enemy Types" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + f"Enemy Types: {q['enemies']}".center(r - l) + line[r:]
        elif "Region:" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + f"{q.get('location', '')}".center(r - l) + line[r:]
        out.append(line)
    return "\n".join(out)


# ── Spell card rendering ──────────────────────────────────────────────────── #

# Substitute spell data into one spell card template.
def _render_spell_card(tpl: str, sp: dict) -> str:
    lines_tpl = tpl.splitlines()
    out: list[str] = []
    for line in lines_tpl:
        if "Spell Name" in line:
            l = line.find("│")
            r = line.rfind("│")
            if l != -1 and r != -1 and r > l:
                line = line[: l + 1] + f"\033[1m{sp['spell_label'].center(r - l - 1)}\033[0m" + line[r:]
        elif "Target: Self/Other" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + f"Target: {sp['target']}".center(r - l) + line[r:]
        elif "Effect: Resist All Types" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + sp["desc"][: r - l].center(r - l) + line[r:]
        elif "Duration: One Day" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + sp["duration"][: r - l].center(r - l) + line[r:]
        out.append(line)
    return "\n".join(out)

# Return display lines for the spell menu — one card per unique spell type.
def build_spell_card_lines(state: dict, compact: bool = False) -> list[str]:
    spells = get_available_spells(state)
    if not spells:
        return ["", "  No wizard spells available (need a Wizard at level 2+).", ""]

    if compact:
        lines: list[str] = ["", "Wizard Spells:"]
        for i, sp in enumerate(spells, start=1):
            status = "(Ready)" if sp["can_cast"] else f"({sp['reason']})"
            lines.append(f"  {i}. \033[1m{sp['spell_label']}\033[0m: {sp['desc']} {status}")
        lines.append("")
        return lines

    try:
        tpl   = _SPELL_CARD_TPL.read_text()
        lines = [""]
        for i, sp in enumerate(spells, start=1):
            status = "[Ready]" if sp["can_cast"] else f"[{sp['reason']}]"
            lines.append(f"  {i}. {status}")
            lines += _render_spell_card(tpl, sp).splitlines()
        return lines
    except Exception:
        lines = ["", "Wizard Spells:"]
        for i, sp in enumerate(spells, start=1):
            status = "(Ready)" if sp["can_cast"] else f"({sp['reason']})"
            lines.append(f"  {i}. \033[1m{sp['spell_label']}\033[0m: {sp['desc']} {status}")
        return lines
