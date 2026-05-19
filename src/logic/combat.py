from __future__ import annotations
import random
import time
from ..utils.state import load_state, save_state


# ── EXP / level tables ───────────────────────────────────────────────────── #

# Cumulative XP thresholds to reach levels 2-5 (heroes start at level 1)
_EXP_LEVEL_THRESHOLDS = [100, 200, 400, 800]


# Return the hero level (1–5) for a given cumulative EXP total.
def exp_to_level(exp: int) -> int:
    level = 1
    for threshold in _EXP_LEVEL_THRESHOLDS:
        if exp >= threshold:
            level += 1
        else:
            break
    return level


# ── Class progression tables ─────────────────────────────────────────────── #

# Max HP per class at levels 1-5
_CLASS_HP: dict[str, list[int]] = {
    "Fighter": [100, 120, 140, 160, 180],
    "Rogue":   [75,  95,  115, 135, 155],
    "Wizard":  [60,  80,  100, 120, 140],
    "Cleric":  [80,  100, 120, 140, 160],
}


# Return max HP for a class at the given level (1-5).
def max_hp_for(hero_class: str, level: int) -> int:
    table = _CLASS_HP.get(hero_class, [100, 120, 140, 160, 180])
    return table[min(max(int(level), 1), 5) - 1]


# Fighter: quest time reduction — see classBonuses.py
# Rogue:   gold bonus            — see classBonuses.py
# Cleric:  HP heal               — see classBonuses.py


# ── Class resistances / weaknesses ───────────────────────────────────────── #
RESIST: dict[str, dict[str, list[str]]] = {
    "Fighter": {"resist": ["Physical"], "weak": ["Magic"],    },  # neutral: Horror
    "Rogue":   {"resist": ["Physical"], "weak": ["Horror"],   },  # neutral: Magic
    "Wizard":  {"resist": ["Magic"],    "weak": ["Physical"], },  # neutral: Horror
    "Cleric":  {"resist": ["Horror"],   "weak": ["Magic"],    },  # neutral: Physical
}


# ── Damage calculation ───────────────────────────────────────────────────── #

# Return damage fraction (0-1) for one hero after a quest roll.
def calc_damage(hero_class: str, enemy_types: str, danger_level: int, mage_armor: bool = False) -> float:
    dl_ranges = {
        1: (0.01, 0.10),
        2: (0.10, 0.20),
        3: (0.20, 0.30),
        4: (0.30, 0.40),
        5: (0.40, 0.50),
    }
    lo, hi = dl_ranges.get(int(danger_level), (0.01, 0.10))
    base     = random.uniform(lo, hi)

    # d20 — natural 20 = no damage
    if random.randint(1, 20) == 20:
        return 0.0

    types    = [t.strip() for t in str(enemy_types).split("/")]
    cfg      = RESIST.get(hero_class, {"resist": [], "weak": []})
    modifier = 1.0
    for t in types:
        if mage_armor:
            modifier *= 0.75  # armor resists all types, negates weaknesses
        else:
            if t in cfg["resist"]:
                modifier *= 0.75
            if t in cfg["weak"]:
                modifier *= 1.50
    return min(1.0, base * modifier)


# ── Regeneration ──────────────────────────────────────────────────────────── #

def apply_regen(state: dict | None = None) -> None:
    own_state   = state is None
    s           = load_state() if own_state else state
    roster      = s.get("roster", [])
    if not roster:
        return
    last = s.get("last_regen")
    if last is None:
        s["last_regen"] = time.time()
        save_state(s)
        return
    try:
        elapsed_min = (time.time() - float(last)) / 60.0
    except Exception:
        elapsed_min = 0.0
    if elapsed_min < 0.01:
        return
    # Heroes currently on a quest don't regen; benched heroes do.
    quest_party: set[str] = set(s.get("quest_party") or [])
    for h in roster:
        if quest_party and h["name"] in quest_party:
            continue
        max_hp = float(h.get("max_hp", 100))
        h["hp"] = min(max_hp, float(h.get("hp", max_hp)) + max_hp * elapsed_min * 0.01)
    s["roster"]     = roster
    s["last_regen"] = time.time()
    save_state(s)