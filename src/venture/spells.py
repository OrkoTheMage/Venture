import datetime
import random
import time
from pathlib import Path

from .state import save_state
from .combat import exp_to_level, max_hp_for

_SPELL_CARD_TPL = Path(__file__).parent / "ascii" / "spellCard.txt"


def _render_spell_card(tpl: str, sp: dict) -> str:
    """Substitute spell data into one spell card template."""
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
                line = line[:l] + f"Target: {sp['target']}".ljust(r - l) + line[r:]
        elif "Effect: Resist All Types" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + sp["desc"][: r - l].ljust(r - l) + line[r:]
        elif "Duration: One Day" in line and "││" in line:
            l = line.find("││") + 2
            r = line.rfind("││")
            if r > l:
                line = line[:l] + sp["duration"][: r - l].ljust(r - l) + line[r:]
        out.append(line)
    return "\n".join(out)


def get_wizard_spells(state: dict) -> list[dict]:
    """Return available wizard spells for all wizards in the roster.

    Each entry: {wizard, spell, desc, can_cast, reason}
    """
    today = datetime.date.today().isoformat()
    cast_log = state.get("spell_cast_log", {})
    spells: list[dict] = []

    for h in state.get("roster", []):
        if h.get("class") != "Wizard":
            continue
        lvl = int(h.get("lvl", 1))
        name = h["name"]
        hero_log = cast_log.get(name, {})

        if lvl >= 2:
            armor_expiry = hero_log.get("mage_armor_until", 0)
            armor_ready = time.time() >= armor_expiry
            spells.append({
                "wizard":      name,
                "spell":       "mage_armor",
                "spell_label": "Mage Armor",
                "desc":        "Resist all damage types for 24h",
                "target":      "Other",
                "duration":    "24h cooldown",
                "can_cast":    armor_ready,
                "reason":      "On cooldown" if not armor_ready else "",
            })

        if lvl >= 3:
            alchemize_expiry = hero_log.get("alchemize_until", 0)
            alchemize_ready = time.time() >= alchemize_expiry
            spells.append({
                "wizard":      name,
                "spell":       "alchemize",
                "spell_label": "Alchemize",
                "desc":        "50% chance: 100G becomes 200G or 0G",
                "target":      "Self",
                "duration":    "24h cooldown",
                "can_cast":    alchemize_ready,
                "reason":      "On cooldown" if not alchemize_ready else "",
            })

        if lvl >= 5:
            already = hero_log.get("inspire") == today
            spells.append({
                "wizard":      name,
                "spell":       "inspire",
                "spell_label": "Inspire",
                "desc":        "Give 300 EXP to a chosen hero",
                "target":      "Other",
                "duration":    "24h cooldown",
                "can_cast":    not already,
                "reason":      "On cooldown" if already else "",
            })

    return spells


def get_available_spells(state: dict) -> list[dict]:
    """Return one entry per unique spell type, marked ready if any wizard can cast it."""
    all_spells = get_wizard_spells(state)
    seen: dict[str, dict] = {}
    for sp in all_spells:
        key = sp["spell"]
        if key not in seen:
            seen[key] = dict(sp)
        elif sp["can_cast"]:
            seen[key]["can_cast"] = True
            seen[key]["reason"] = ""
    return list(seen.values())


def get_casters_for_spell(state: dict, spell: str) -> list[dict]:
    """Return all wizards who have access to the given spell, with cast status."""
    return [sp for sp in get_wizard_spells(state) if sp["spell"] == spell]


def build_spell_card_lines(state: dict, compact: bool = False) -> list[str]:
    """Return display lines for the spell menu — one card per unique spell type."""
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
        tpl = _SPELL_CARD_TPL.read_text()
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


def cast_wizard_spell(
    state: dict, wizard_name: str, spell: str, target_hero: str | None = None
) -> tuple[bool, str]:
    """Cast a wizard spell. Returns (success, message)."""
    today = datetime.date.today().isoformat()

    roster = state.get("roster", [])
    wizard = next((h for h in roster if h["name"] == wizard_name), None)
    if wizard is None:
        return False, f"{wizard_name} not found in roster."
    if wizard.get("class") != "Wizard":
        return False, f"{wizard_name} is not a Wizard."

    lvl = int(wizard.get("lvl", 1))
    cast_log = state.setdefault("spell_cast_log", {})
    hero_log = cast_log.setdefault(wizard_name, {})

    if spell == "alchemize":
        if hero_log.get("alchemize_until", 0) > time.time():
            return False, "Alchemize is still on cooldown."
        gold = int(state.get("gold", 0))
        if gold < 100:
            return False, f"Not enough gold. Need 100G, have {gold}G."
        state["gold"] = gold - 100
        expiry = time.time() + 86400
        hero_log["alchemize_until"] = expiry
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
        target = next(
            (h for h in roster if h["name"].lower() == target_hero.lower()), None
        )
        if target is None:
            return False, f"Hero '{target_hero}' not found."
        expiry = time.time() + 86400
        state.setdefault("mage_armor", {})[target["name"]] = expiry
        hero_log["mage_armor_until"] = expiry
        state["roster"] = roster
        save_state(state)
        return True, f"{target['name']} is protected by Mage Armor for 24 hours."

    if spell == "inspire":
        if lvl < 5:
            return False, f"{wizard_name} needs level 5 to cast Inspire."
        if hero_log.get("inspire") == today:
            return False, "Inspire already cast today."
        if target_hero is None:
            return False, "Inspire requires a target hero."
        target = next(
            (h for h in roster if h["name"].lower() == target_hero.lower()), None
        )
        if target is None:
            return False, f"Hero '{target_hero}' not found."
        target["exp"] = int(target.get("exp", 0)) + 300
        new_lvl = exp_to_level(target["exp"])
        old_lvl = int(target.get("lvl", 1))
        target["lvl"] = new_lvl
        if new_lvl != old_lvl:
            old_max = float(target.get("max_hp", 100))
            new_max = float(max_hp_for(target.get("class", "Fighter"), new_lvl))
            if old_max > 0:
                target["hp"] = min(new_max, float(target.get("hp", old_max)) / old_max * new_max)
            target["max_hp"] = new_max
        hero_log["inspire"] = today
        state["roster"] = roster
        save_state(state)
        level_msg = f" (leveled up to {new_lvl}!)" if new_lvl != old_lvl else ""
        return True, f"{target['name']} gained 300 EXP{level_msg}."

    return False, f"Unknown spell '{spell}'."
