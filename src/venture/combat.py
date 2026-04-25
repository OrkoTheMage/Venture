import random
import time

from .state import load_state, save_state

# Cumulative XP thresholds to reach levels 2-5 (heroes start at level 1)
_EXP_LEVEL_THRESHOLDS = [100, 200, 400, 800]

# ── Class progression tables ───────────────────────────────────────────────── #

# Max HP per class at levels 1-5
_CLASS_HP: dict[str, list[int]] = {
    "Fighter": [100, 120, 140, 160, 180],
    "Rogue":   [75,  95,  115, 135, 155],
    "Wizard":  [60,  80,  100, 120, 140],
    "Cleric":  [80,  100, 120, 140, 160],
}


def max_hp_for(hero_class: str, level: int) -> int:
    """Return max HP for a class at the given level (1-5)."""
    table = _CLASS_HP.get(hero_class, [100, 120, 140, 160, 180])
    return table[min(max(int(level), 1), 5) - 1]


# Fighter: quest time reduction (fraction) per level
_FIGHTER_TIME_REDUCTION: dict[int, float] = {2: 0.12, 3: 0.24, 4: 0.38, 5: 0.50}

# Cleric: post-quest HP heal percent per level
_CLERIC_HEAL_PCT: dict[int, float] = {2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}


def exp_to_level(exp: int) -> int:
    """Return the hero level (1–5) for a given cumulative EXP total."""
    level = 1
    for threshold in _EXP_LEVEL_THRESHOLDS:
        if exp >= threshold:
            level += 1
        else:
            break
    return level


# ── class resistances / weaknesses ────────────────────────────────────────── #
RESIST: dict[str, dict[str, list[str]]] = {
    "Fighter": {"resist": ["Physical"], "weak": ["Magic"]},
    "Rogue":   {"resist": [],           "weak": ["Magic", "Physical"]},
    "Wizard":  {"resist": ["Magic"],    "weak": ["Physical"]},
    "Cleric":  {"resist": ["Horror"],   "weak": ["Physical"]},
}


def calc_damage(hero_class: str, enemy_types: str, danger_level: int) -> float:
    """Return damage fraction (0-1) for one hero after a quest roll."""
    dl_ranges = {
        1: (0.01, 0.10),
        2: (0.10, 0.20),
        3: (0.20, 0.30),
        4: (0.30, 0.40),
        5: (0.40, 0.50),
    }
    lo, hi = dl_ranges.get(int(danger_level), (0.01, 0.10))
    base = random.uniform(lo, hi)

    # d20 — natural 20 = no damage
    if random.randint(1, 20) == 20:
        return 0.0

    types = [t.strip() for t in str(enemy_types).split("/")]
    cfg = RESIST.get(hero_class, {"resist": [], "weak": []})
    modifier = 1.0
    for t in types:
        if t in cfg["resist"]:
            modifier *= 0.75
        if t in cfg["weak"]:
            modifier *= 1.50
    return min(1.0, base * modifier)


def apply_regen() -> None:
    """Regenerate 1% max_hp per minute while no quest is active."""
    s = load_state()
    if s.get("quest_start"):
        return
    roster = s.get("roster", [])
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
    for h in roster:
        max_hp = float(h.get("max_hp", 100))
        h["hp"] = min(max_hp, float(h.get("hp", max_hp)) + max_hp * elapsed_min * 0.01)
    s["roster"] = roster
    s["last_regen"] = time.time()
    save_state(s)



