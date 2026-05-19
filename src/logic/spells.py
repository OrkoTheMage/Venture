from __future__ import annotations

import random
import time

from ..utils.state import save_state
from .combat import exp_to_level, max_hp_for


# ── Spell definitions ─────────────────────────────────────────────────────── #

# Return available wizard spells for all wizards in the roster.
# Each entry: {wizard, spell, desc, can_cast, reason}
def get_wizard_spells(state: dict) -> list[dict]:
    cast_log = state.get("spell_cast_log", {})
    spells: list[dict] = []

    for h in state.get("roster", []):
        if h.get("class") != "Wizard":
            continue
        lvl      = int(h.get("lvl", 1))
        name     = h["name"]
        hero_log = cast_log.get(name, {})

        if lvl >= 2:
            armor_expiry = hero_log.get("mage_armor_until", 0)
            armor_ready  = time.time() >= armor_expiry
            spells.append({
                "wizard":      name,
                "spell":       "mage_armor",
                "spell_label": "Mage Armor",
                "desc":        "Resist all damage types, 3 weeks",
                "target":      "Any",
                "duration":    "1h cooldown",
                "can_cast":    armor_ready,
                "reason":      "On cooldown" if not armor_ready else "",
            })

        if lvl >= 3:
            alchemize_expiry = hero_log.get("alchemize_until", 0)
            alchemize_ready  = time.time() >= alchemize_expiry
            spells.append({
                "wizard":      name,
                "spell":       "alchemize",
                "spell_label": "Alchemize",
                "desc":        "50% chance: 100G becomes 200G or 0G",
                "target":      "Self",
                "duration":    "1h cooldown",
                "can_cast":    alchemize_ready,
                "reason":      "On cooldown" if not alchemize_ready else "",
            })

        if lvl >= 4:
            portal_expiry = hero_log.get("portal_until", 0)
            portal_ready  = time.time() >= portal_expiry
            spells.append({
                "wizard":      name,
                "spell":       "portal",
                "spell_label": "Portal",
                "desc":        "Your next quest finishes instantly",
                "target":      "Self",
                "duration":    "12h cooldown",
                "can_cast":    portal_ready,
                "reason":      "On cooldown" if not portal_ready else "",
            })

        if lvl >= 5:
            inspire_expiry = hero_log.get("inspire_until", 0)
            inspire_ready  = time.time() >= inspire_expiry
            spells.append({
                "wizard":      name,
                "spell":       "inspire",
                "spell_label": "Inspire",
                "desc":        "Give 300 EXP to a chosen hero",
                "target":      "Other",
                "duration":    "24h cooldown",
                "can_cast":    inspire_ready,
                "reason":      "On cooldown" if not inspire_ready else "",
            })

    return spells

# Return one entry per unique spell type, marked ready if any wizard can cast it.
def get_available_spells(state: dict) -> list[dict]:
    all_spells = get_wizard_spells(state)
    seen: dict[str, dict] = {}
    for sp in all_spells:
        key = sp["spell"]
        if key not in seen:
            seen[key] = dict(sp)
        elif sp["can_cast"]:
            seen[key]["can_cast"] = True
            seen[key]["reason"]   = ""
    return list(seen.values())

# Return all wizards who have access to the given spell, with cast status.
def get_casters_for_spell(state: dict, spell: str) -> list[dict]:
    return [sp for sp in get_wizard_spells(state) if sp["spell"] == spell]


# ── Spell casting ─────────────────────────────────────────────────────────── #

# Cast a wizard spell. Returns (success, message).
def cast_wizard_spell(
    state: dict, wizard_name: str, spell: str, target_hero: str | None = None
) -> tuple[bool, str]:
    roster = state.get("roster", [])
    wizard = next((h for h in roster if h["name"] == wizard_name), None)
    if wizard is None:
        return False, f"{wizard_name} not found in roster."
    if wizard.get("class") != "Wizard":
        return False, f"{wizard_name} is not a Wizard."

    lvl      = int(wizard.get("lvl", 1))
    cast_log = state.setdefault("spell_cast_log", {})
    hero_log = cast_log.setdefault(wizard_name, {})

    if spell == "alchemize":
        if hero_log.get("alchemize_until", 0) > time.time():
            return False, "Alchemize is still on cooldown."
        gold = int(state.get("gold", 0))
        if gold < 100:
            return False, f"Not enough gold. Need 100G, have {gold}G."
        state["gold"] = gold - 100
        hero_log["alchemize_until"] = time.time() + 3600
        save_state(state)
        if random.random() < 0.5:
            state["gold"] = state["gold"] + 200
            save_state(state)
            return True, "The ritual succeeds! 100G transmuted into 200G."
        else:
            save_state(state)
            return True, "The ritual fails. The gold crumbles to ash. (-100G)"

    if spell == "mage_armor":
        if hero_log.get("mage_armor_until", 0) > time.time():
            return False, "Mage Armor is still on cooldown."
        if target_hero is None:
            return False, "Mage Armor requires a target hero."
        target = next((h for h in roster if h["name"].lower() == target_hero.lower()), None)
        if target is None:
            return False, f"Hero '{target_hero}' not found."
        state.setdefault("mage_armor", {})[target["name"]] = 3
        hero_log["mage_armor_until"] = time.time() + 3600
        state["roster"] = roster
        save_state(state)
        return True, f"{target['name']} is protected by Mage Armor for 3 quests."

    if spell == "portal":
        if hero_log.get("portal_until", 0) > time.time():
            return False, "Portal is still on cooldown."
        if state.get("portal_active"):
            return False, "A portal has already been opened this week."
        state["portal_active"] = True
        hero_log["portal_until"] = time.time() + 43200
        save_state(state)
        return True, "A portal opens — your party's quest finishes instantly!"

    if spell == "inspire":
        if lvl < 5:
            return False, f"{wizard_name} needs level 5 to cast Inspire."
        if hero_log.get("inspire_until", 0) > time.time():
            return False, "Inspire is still on cooldown."
        if target_hero is None:
            return False, "Inspire requires a target hero."
        target = next((h for h in roster if h["name"].lower() == target_hero.lower()), None)
        if target is None:
            return False, f"Hero '{target_hero}' not found."
        target["exp"] = int(target.get("exp", 0)) + 300
        new_lvl       = exp_to_level(target["exp"])
        old_lvl       = int(target.get("lvl", 1))
        target["lvl"] = new_lvl
        if new_lvl != old_lvl:
            old_max        = float(target.get("max_hp", 100))
            new_max        = float(max_hp_for(target.get("class", "Fighter"), new_lvl))
            if old_max > 0:
                target["hp"] = min(new_max, float(target.get("hp", old_max)) / old_max * new_max)
            target["max_hp"] = new_max
        hero_log["inspire_until"] = time.time() + 86400
        state["roster"] = roster
        save_state(state)
        level_msg = f" (leveled up to {new_lvl}!)" if new_lvl != old_lvl else ""
        return True, f"{target['name']} gained 300 EXP{level_msg}."

    return False, f"Unknown spell '{spell}'."
