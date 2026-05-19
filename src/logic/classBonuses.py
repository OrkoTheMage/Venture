from __future__ import annotations


# ── Class bonus tables ────────────────────────────────────────────────────── #
# Per-level special bonuses that apply during and after quests.

# Fighter: multiplicative quest time reduction per level
FIGHTER_TIME_REDUCTION: dict[int, float] = {2: 0.12, 3: 0.24, 4: 0.38, 5: 0.50}

# Rogue: bonus gold fraction per level (added on top of base quest gold)
ROGUE_GOLD_BONUS: dict[int, float] = {2: 0.12, 3: 0.24, 4: 0.38, 5: 0.50}

# Cleric: post-quest HP heal fraction of max_hp per level
CLERIC_HEAL_PCT: dict[int, float] = {2: 0.10, 3: 0.15, 4: 0.20, 5: 0.25}
