"""Party selection screen builder."""

from __future__ import annotations

import textwrap
import time

from .classBonuses import FIGHTER_TIME_REDUCTION
from .combat import RESIST
from .quest import _LENGTH_SECONDS, format_duration
from .questDefinitions import QUEST_LORE


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
) -> list[str]:
    """Return display lines for the party selection screen."""
    title = f"Select party for: \033[1m{quest_name}\033[0m"
    if danger:
        title += f"  (Level {danger})"
    lines: list[str] = [title, ""]

    # Lore paragraph — word-wrapped to fit the window
    lore = QUEST_LORE.get(quest_name)
    if lore:
        for wrapped_line in textwrap.wrap(lore, width=max(20, width - 2)):
            lines.append(f"  {wrapped_line}")
        lines.append("")

    # Enemy type tooltip
    if enemy_types:
        lines.append(f"  Enemies: {enemy_types}")
        # Show quest duration adjusted for selected Fighters
        base_dur = _LENGTH_SECONDS.get(length, 300)
        dur_multiplier = 1.0
        for s_idx in selected:
            if 0 <= s_idx < len(roster):
                hero = roster[s_idx]
                if hero.get("class") == "Fighter":
                    reduction = FIGHTER_TIME_REDUCTION.get(int(hero.get("lvl", 1)), 0.0)
                    dur_multiplier *= (1.0 - reduction)
        adj_dur = max(1, int(base_dur * dur_multiplier))
        lines.append(f"  Duration: {format_duration(adj_dur)}")
        lines.append("")

    mage_armor_map = (state or {}).get("mage_armor", {})
    now = time.time()

    lines.append(f"Choose {max_party} heroes  ({len(selected)}/{max_party} selected)")
    lines.append("")
    for i, h in enumerate(roster, start=1):
        marker = "[x]" if (i - 1) in selected else "[ ]"
        hp_pct = int(float(h.get("hp", 100)) / max(1.0, float(h.get("max_hp", 100))) * 100)
        hero_class = h.get("class", "")
        cfg = RESIST.get(hero_class, {"resist": [], "weak": []})
        has_armor = mage_armor_map.get(h["name"], 0) > now
        if enemy_types:
            types = [t.strip() for t in enemy_types.split("/")]
            if has_armor:
                tip = "  [Mage Armor] RES: All"
            else:
                resists = [t for t in types if t in cfg["resist"]]
                weaks   = [t for t in types if t in cfg["weak"]]
                if resists and weaks:
                    tip = f"  RES: {', '.join(resists)}  WEAK: {', '.join(weaks)}"
                elif resists:
                    tip = f"  RES: {', '.join(resists)}"
                elif weaks:
                    tip = f"  WEAK: {', '.join(weaks)}"
                else:
                    tip = "  Neutral"
        else:
            tip = "  [Mage Armor]" if has_armor else ""
        lines.append(
            f"  {marker} {i}. {h['name']:<12} {h['class']:<8}  Lvl {h['lvl']}  HP {hp_pct}%{tip}"
        )
    lines.append("")
    return lines
