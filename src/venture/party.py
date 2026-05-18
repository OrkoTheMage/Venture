"""Party selection screen builder."""

from __future__ import annotations

import math
import textwrap

from .classBonuses import FIGHTER_TIME_REDUCTION
from .combat import RESIST
from .quest import _LENGTH_SECONDS, format_duration
from .questDefinitions import QUEST_LORE, render_lore, lore_line_count


def compact_info_height(quest_name: str, width: int, enemy_types: str) -> int:
    """Lines occupied by the compact info block (header through Choose+blank).
    Does NOT include hero rows, nav hint, or trailing blank.
    """
    n = 4  # header + blank + "Choose" line + blank
    if enemy_types:
        n += 2  # enemies/duration line + blank
    lore = QUEST_LORE.get(quest_name, "")
    if lore:
        n += lore_line_count(lore, width=max(20, width - 4)) + 1  # lore lines + blank
    return n


def compact_heroes_per_page(quest_name: str, width: int, enemy_types: str, win_height: int) -> int:
    """Max hero rows that fit on one page in compact mode.

    Accounts for: info block (without choose/blank) + choose(1) + blank(1)
    + heroes + blank(1) + nav hint(1) + trailing blank(1).
    The trailing blank overflows by 1 and is safely clipped by win.render.
    """
    info_h = compact_info_height(quest_name, width, enemy_types)
    # info_h includes choose+blank (+2); build_party_screen adds those after
    # computing per_page, so effective info at calc time = info_h - 2.
    # per_page = win_height - (info_h - 2) - 4  [choose+blank+blank+nav = 4]
    return max(3, win_height - info_h - 2)


def build_party_screen(
    quest_name: str,
    roster: list[dict],
    selected: list[int],
    max_party: int,
    width: int = 80,
    enemy_types: str = "",
    danger: int = 0,
    length: str = "Short",
    state: dict | None = None,
    compact: bool = False,
    hero_page: int = 0,
    win_height: int | None = None,
    location: str = "",
) -> list[str]:
    """Return display lines for the party selection screen."""
    mage_armor_map = (state or {}).get("mage_armor", {})
# Adjusted duration (Fighter bonus applied to selected heroes)
    base_dur = _LENGTH_SECONDS.get(length, 300)
    dur_multiplier = 1.0
    for s_idx in selected:
        if 0 <= s_idx < len(roster):
            hero = roster[s_idx]
            if hero.get("class") == "Fighter":
                reduction = FIGHTER_TIME_REDUCTION.get(int(hero.get("lvl", 1)), 0.0)
                dur_multiplier *= (1.0 - reduction)
    adj_dur = max(1, int(base_dur * dur_multiplier))

    idx_w = len(str(len(roster)))  # consistent index column width across all rows

    def _hero_tip(h: dict) -> str:
        hero_class = h.get("class", "")
        cfg = RESIST.get(hero_class, {"resist": [], "weak": []})
        has_armor = mage_armor_map.get(h["name"], 0) > 0
        if enemy_types:
            types = [t.strip() for t in enemy_types.split("/")]
            if has_armor:
                return "  [Mage Armor] RES: All"
            resists = [t for t in types if t in cfg["resist"]]
            weaks   = [t for t in types if t in cfg["weak"]]
            if resists and weaks:
                return f"  RES: {', '.join(resists)}  WEAK: {', '.join(weaks)}"
            elif resists:
                return f"  RES: {', '.join(resists)}"
            elif weaks:
                return f"  WEAK: {', '.join(weaks)}"
            return "  Neutral"
        return "  [Mage Armor]" if has_armor else ""

    def _hero_row(i: int, h: dict) -> str:
        marker = "[x]" if (i - 1) in selected else "[ ]"
        hp_pct = int(float(h.get("hp", 100)) / max(1.0, float(h.get("max_hp", 100))) * 100)
        name   = h["name"][:12]
        return (
            f"  {marker} {i:>{idx_w}}. {name:<12} {h['class']:<8}"
            f"  Lvl {h['lvl']}  HP {hp_pct:>3}%{_hero_tip(h)}"
        )

    # ── Compact layout ───────────────────────────────────────────────────── #
    if compact:
        header = f"\033[1m{quest_name}"
        if location:
            header += f" | {location}"
        header += "\033[0m"
        if danger:
            header += f"  (Danger: {danger} | {length})"

        # Fixed info block (header → Choose → blank)
        info: list[str] = [header, ""]
        if enemy_types:
            info.append(f"  Enemies: \033[1m{enemy_types}\033[0m  |  Duration: \033[1m{format_duration(adj_dur)}\033[0m")
            info.append("")
        lore = QUEST_LORE.get(quest_name)
        if lore:
            for wrapped_line in render_lore(lore, width=max(20, width - 4), indent=""):
                info.append(f"  {wrapped_line}")
            info.append("")

        # Calculate pagination
        n_roster = len(roster)
        if win_height is not None:
            per_page = max(3, win_height - len(info) - 4)
            # ^ len(info) + choose(1) + blank(1) + heroes(per_page) + blank(1) + nav(1) + trailing(1) = win_height + 1
            # the +1 overflow is safely clipped by win.render
        else:
            per_page = n_roster

        total_pages = max(1, math.ceil(n_roster / per_page))
        hero_page   = max(0, min(hero_page, total_pages - 1))
        page_start  = hero_page * per_page
        page_end    = min(page_start + per_page, n_roster)

        # Choose line — include page indicator when paginated
        choose = f"\033[1mChoose {max_party} heroes  ({len(selected)}/{max_party} selected)\033[0m"
        if total_pages > 1:
            choose += f"   Page {hero_page + 1}/{total_pages}"
        info.append(choose)
        info.append("")

        lines = list(info)
        for i, h in enumerate(roster[page_start:page_end], start=page_start + 1):
            lines.append(_hero_row(i, h))

        if total_pages > 1:
            lines.append("")
            lines.append("  'n' next page  \u00b7  'p' prev page")

        lines.append("")
        return lines

    # ── Regular layout ───────────────────────────────────────────────────── #
    title = "Select party for: "
    title += f"\033[1m{quest_name}"
    if location:
        title += f" | {location}"
    title += "\033[0m"
    if danger:
        title += f"  (Danger: {danger} | {length})"
    lines = [title, ""]

    lore = QUEST_LORE.get(quest_name)
    if lore:
        for wrapped_line in render_lore(lore, width=max(20, width - 2), indent=""):
            lines.append(f"  {wrapped_line}")
        lines.append("")

    if enemy_types:
        lines.append(f"  Enemies: \033[1m{enemy_types}\033[0m")
        lines.append(f"  Duration: \033[1m{format_duration(adj_dur)}\033[0m")
        lines.append("")

    lines.append(f"\033[1mChoose {max_party} heroes  ({len(selected)}/{max_party} selected)\033[0m")
    lines.append("")
    for i, h in enumerate(roster, start=1):
        lines.append(_hero_row(i, h))
    lines.append("")
    return lines
