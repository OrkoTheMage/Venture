import random
import time
from pathlib import Path

from .state import load_state, save_state
from .combat import (
    calc_damage, exp_to_level, max_hp_for,
    _FIGHTER_TIME_REDUCTION, _CLERIC_HEAL_PCT,
)

# ── EXP constants ─────────────────────────────────────────────────────────── #
_EXP_FOR_LENGTH: dict[str, int] = {"Short": 20, "Medium": 30, "Long": 40}
_EXP_FOR_DANGER: dict[int, int] = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}

_CARD_TPL = Path(__file__).parent / "ascii" / "questCard.txt"
_ALLOWED_TYPES = ["Physical", "Magic", "Horror"]
_LENGTH_SECONDS = {"Short": 300, "Medium": 1800, "Long": 3600}

# ── Quest definitions ─────────────────────────────────────────────────────── #
_INITIAL_QUEST = [
    {"name": "Gather Allies", "danger": 1, "length": "Short", "enemies": "Physical"},
]
_REGULAR_QUESTS = [
    {"name": "The Haunted Mill", "danger": 2, "length": "Short"},
    {"name": "Bandit Ambush",    "danger": 4, "length": "Short"},
    {"name": "Deep Cavern",      "danger": 5, "length": "Long"},
]


def _assign_enemies(quests: list[dict]) -> None:
    """Fill in random enemy types for any quest that doesn't have one yet."""
    for q in quests:
        if q.get("enemies"):
            continue
        if int(q.get("danger", 1)) >= 4:
            if random.choice((True, False)):
                a, b = random.sample(_ALLOWED_TYPES, 2)
                q["enemies"] = f"{a}/{b}"
            else:
                q["enemies"] = random.choice(_ALLOWED_TYPES)
        else:
            q["enemies"] = random.choice(_ALLOWED_TYPES)


def _render_quest_card(tpl: str, q: dict) -> str:
    """Substitute quest data into one quest card template."""
    lines_tpl = tpl.splitlines()
    out: list[str] = []
    for line in lines_tpl:
        if "Quest Name" in line:
            l = line.find("│")
            r = line.rfind("│")
            if l != -1 and r != -1 and r > l:
                line = line[: l + 1] + q["name"].center(r - l - 1) + line[r:]
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
                label = "Enemy Types: "
                padded = str(q["enemies"]).center(r - l - len(label))
                line = line[:l] + label + padded + line[r:]
        out.append(line)
    return "\n".join(out)


def build_quest_cards(state: dict) -> tuple[list[dict], list[str]]:
    """Return (quests list, display lines) for the current quest menu."""
    import copy
    if not state.get("gather_allies_done"):
        quests = copy.deepcopy(_INITIAL_QUEST)
    else:
        quests = copy.deepcopy(_REGULAR_QUESTS)

    _assign_enemies(quests)

    try:
        tpl = _CARD_TPL.read_text()
        cards_text = ""
        for i, q in enumerate(quests, start=1):
            cards_text += f" {i}.\n" + _render_quest_card(tpl, q) + "\n\n"
        return quests, cards_text.splitlines()
    except Exception:
        fallback = [
            f"{i}. {q['name']} - Danger {q['danger']} - {q['length']} - {q['enemies']}"
            for i, q in enumerate(quests, start=1)
        ]
        return quests, fallback


def build_party_screen(quest_name: str, roster: list[dict], selected: list[int], max_party: int) -> list[str]:
    """Return display lines for the party selection screen."""
    lines = [
        f"Select party for: {quest_name}",
        f"Choose {max_party} heroes  ({len(selected)}/{max_party} selected)",
        "",
    ]
    for i, h in enumerate(roster, start=1):
        marker = "[x]" if (i - 1) in selected else "[ ]"
        hp_pct = int(float(h.get("hp", 100)) / max(1.0, float(h.get("max_hp", 100))) * 100)
        lines.append(f"  {marker} {i}. {h['name']:<12} {h['class']:<8}  Lvl {h['lvl']}  HP {hp_pct}%")
    lines += ["", "Type a number to toggle, 'go' to confirm, 'back' to cancel."]
    return lines


def _award_exp(hero: dict, quest_exp: int) -> None:
    """Add quest_exp to a hero and update their level and max_hp in-place."""
    new_exp = int(hero.get("exp", 0)) + quest_exp
    hero["exp"] = new_exp
    new_level = exp_to_level(new_exp)
    old_level = int(hero.get("lvl", 1))
    hero["lvl"] = new_level
    if new_level != old_level:
        old_max = float(hero.get("max_hp", 100))
        new_max = float(max_hp_for(hero.get("class", "Fighter"), new_level))
        if old_max > 0:
            hero["hp"] = min(new_max, float(hero.get("hp", old_max)) / old_max * new_max)
        hero["max_hp"] = new_max


def _apply_scripted_rewards(s: dict) -> list[str]:
    """Apply scripted quest rewards to state. Returns reward description strings."""
    rewards: list[str] = []
    if s.get("quest_name") == "Gather Allies":
        new_heroes = [
            {"name": "Grandlaff", "class": "Wizard", "lvl": 1, "hp": 60, "max_hp": 60, "exp": 0},
            {"name": "Lora",      "class": "Cleric", "lvl": 1, "hp": 80, "max_hp": 80, "exp": 0},
        ]
        existing = {h["name"].lower() for h in s["roster"]}
        for hero in new_heroes:
            if hero["name"].lower() not in existing:
                s["roster"].append(hero)
                rewards.append(f"{hero['name']} the {hero['class']} joins your roster")
        s["gather_allies_done"] = True
    return rewards


def apply_quest_damage() -> dict:
    """Apply damage to quest party on completion and clear quest keys.
    Returns a summary dict: {damage_taken: [(name, hp_pct_lost, exp_gained)], rewards: [str], fallen: [str]}.
    """
    s = load_state()
    roster = s.get("roster", [])
    enemy_types = s.get("quest_enemies", "Physical")
    danger = int(s.get("quest_danger", s.get("quest_id", 1)))
    length = s.get("quest_length", "Short")
    quest_name = s.get("quest_name", "")
    party_names = s.get("quest_party")  # None = all heroes (e.g. Gather Allies)

    quest_exp = _EXP_FOR_LENGTH.get(length, 20) + _EXP_FOR_DANGER.get(danger, 10)

    damage_taken: list[tuple[str, int, int]] = []
    fallen: list[str] = []
    for h in roster:
        if party_names is not None and h["name"] not in party_names:
            continue
        dmg = calc_damage(h.get("class", "Fighter"), enemy_types, danger)
        max_hp = float(h.get("max_hp", 100))
        hp_lost = max_hp * dmg
        h["hp"] = max(0.0, float(h.get("hp", max_hp)) - hp_lost)
        if h["hp"] == 0.0:
            fallen.append(h["name"])
            damage_taken.append((h["name"], int(dmg * 100), 0))
        else:
            _award_exp(h, quest_exp)
            damage_taken.append((h["name"], int(dmg * 100), quest_exp))

    # Cleric: heal a random living party hero after combat
    living_party = [
        h for h in roster
        if h["name"] not in fallen
        and (party_names is None or h["name"] in party_names)
    ]
    best_cleric_lvl = max(
        (int(h.get("lvl", 1)) for h in living_party if h.get("class") == "Cleric"),
        default=0,
    )
    heal_pct = _CLERIC_HEAL_PCT.get(best_cleric_lvl, 0.0)
    cleric_rewards: list[str] = []
    if heal_pct > 0 and living_party:
        target = random.choice(living_party)
        old_hp = float(target.get("hp", 0))
        max_hp_val = float(target.get("max_hp", 100))
        target["hp"] = min(max_hp_val, old_hp + max_hp_val * heal_pct)
        healed_pct = int((target["hp"] - old_hp) / max_hp_val * 100)
        if healed_pct > 0:
            cleric_rewards.append(f"Cleric blessed {target['name']}: +{healed_pct}% HP restored")

    s["roster"] = [h for h in roster if h["name"] not in fallen]

    rewards = _apply_scripted_rewards(s) + cleric_rewards

    for key in (
        "quest_start", "quest_id", "quest_name", "quest_danger",
        "quest_enemies", "quest_length", "quest_duration", "quest_party",
    ):
        s.pop(key, None)
    s["last_regen"] = time.time()
    save_state(s)
    return {"damage_taken": damage_taken, "rewards": rewards, "fallen": fallen}


def quest_info() -> dict:
    """Return timing info for the active quest, or {'running': False} if none."""
    s = load_state()
    start = s.get("quest_start")
    if start is None:
        return {"running": False}
    try:
        start = float(start)
        duration = float(s.get("quest_duration", 60))
    except Exception:
        return {"running": False}
    elapsed = time.time() - start
    remaining = max(0.0, duration - elapsed)
    completed = elapsed >= duration
    return {
        "running": not completed,
        "elapsed": max(0.0, elapsed),
        "remaining": remaining,
        "completed": completed,
        "duration": duration,
    }


def start_quest(state: dict, chosen: dict, party: list[dict]) -> None:
    """Persist all quest keys into state and save."""
    length = chosen.get("length", "Short")
    dur = _LENGTH_SECONDS.get(length, 300)
    # Fighter bonus: best time reduction among Fighters in party
    best_reduction = max(
        (_FIGHTER_TIME_REDUCTION.get(int(h.get("lvl", 1)), 0.0)
         for h in party if h.get("class") == "Fighter"),
        default=0.0,
    )
    if best_reduction > 0:
        dur = max(1, int(dur * (1.0 - best_reduction)))
    state.update({
        "quest_start":    time.time(),
        "quest_id":       chosen.get("_index", 1),
        "quest_name":     chosen["name"],
        "quest_danger":   int(chosen["danger"]),
        "quest_enemies":  chosen["enemies"],
        "quest_length":   length,
        "quest_duration": dur,
        "quest_party":    [h["name"] for h in party],
    })
    save_state(state)


# ── Wizard spells ──────────────────────────────────────────────────────────── #

def get_wizard_spells(state: dict) -> list[dict]:
    """Return available wizard spells for all wizards in the roster.

    Each entry: {wizard, spell, desc, can_cast, reason}
    """
    import datetime
    today = datetime.date.today().isoformat()
    cast_log = state.get("spell_cast_log", {})
    spells: list[dict] = []

    for h in state.get("roster", []):
        if h.get("class") != "Wizard":
            continue
        lvl = int(h.get("lvl", 1))
        name = h["name"]
        hero_log = cast_log.get(name, {})

        if lvl >= 5:
            already = hero_log.get("inspire") == today
            spells.append({
                "wizard":    name,
                "spell":     "inspire",
                "desc":      "Give 300 EXP to a chosen hero",
                "can_cast":  not already,
                "reason":    "Already cast today" if already else "",
            })

    return spells


def cast_wizard_spell(
    state: dict, wizard_name: str, spell: str, target_hero: str | None = None
) -> tuple[bool, str]:
    """Cast a wizard spell. Returns (success, message)."""
    import datetime
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
