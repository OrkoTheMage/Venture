import copy
import random
import textwrap
import time
from pathlib import Path

from .state import load_state, save_state
from .combat import (
    calc_damage, exp_to_level, max_hp_for,
    RESIST,
)
from .classBonuses import FIGHTER_TIME_REDUCTION, CLERIC_HEAL_PCT, ROGUE_GOLD_BONUS
from .spells import (
    build_spell_card_lines,
    cast_wizard_spell,
    get_available_spells,
    get_casters_for_spell,
)
from .recruit import build_recruit_offers, hire_recruit
from .graveyard import build_graveyard_lines, record_fallen
from .questDefinitions import (
    QUEST_LORE,
    QUEST_POOL,
    INITIAL_QUEST,
    BOSS_QUEST_FAMILY_BUSINESS,
    BOSS_QUEST_SINS_OF_THE_FATHER,
)

# ── EXP constants ─────────────────────────────────────────────────────────── #
_EXP_FOR_LENGTH: dict[str, int] = {"Short": 20, "Medium": 30, "Long": 40}
_EXP_FOR_DANGER: dict[int, int] = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}

_GOLD_FOR_DANGER: dict[int, int] = {1: 10, 2: 20, 3: 40, 4: 80, 5: 160}
_GOLD_FOR_LENGTH: dict[str, int] = {"Short": 10, "Medium": 50, "Long": 100}

_CARD_TPL = Path(__file__).parent / "ascii" / "questCard.txt"
_ALLOWED_TYPES = ["Physical", "Magic", "Horror"]
_LENGTH_SECONDS = {"Short": 300, "Medium": 1800, "Long": 3600}


def format_duration(seconds: float | int) -> str:
    try:
        total = int(max(0, float(seconds)))
    except Exception:
        total = 0
    mins, secs = divmod(total, 60)
    return f"{mins}m {secs}s"

# ── Quest card rendering ─────────────────────────────────────────────────── #
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
        out.append(line)
    return "\n".join(out)


def build_quest_cards(state: dict, compact: bool = False) -> tuple[list[dict], list[str]]:
    # Use persisted quests if already rolled; otherwise generate and save them
    if state.get("available_quests"):
        quests = state["available_quests"]
    else:
        if not state.get("gather_allies_done"):
            quests = copy.deepcopy(INITIAL_QUEST)
        else:
            picked = random.sample(QUEST_POOL, min(3, len(QUEST_POOL)))
            danger_ranges = [
                random.randint(1, 2),  # slot 1: easy
                random.randint(3, 4),  # slot 2: mid
                random.randint(4, 5),  # slot 3: hard
            ]
            quests = []
            for i, q in enumerate(picked):
                danger = danger_ranges[i]
                enemies = q["enemies"]
                if danger < 4 and "/" in enemies:
                    enemies = random.choice(enemies.split("/"))
                quests.append({
                    "name":    q["name"],
                    "enemies": enemies,
                    "danger":  danger,
                    "length":  random.choice(["Short", "Medium", "Long"]),
                })
            # Inject boss quest into slot 3 if eligible and not yet completed
            roster = state.get("roster", [])
            graveyard = state.get("graveyard", [])
            # Persist these flags once True so dismissed heroes don't erase eligibility
            if not state.get("has_had_lvl3") and (
                any(int(h.get("lvl", 1)) >= 3 for h in roster) or
                any(int(e.get("lvl", 1)) >= 3 for e in graveyard)
            ):
                state["has_had_lvl3"] = True
            if not state.get("has_had_lvl5") and (
                any(int(h.get("lvl", 1)) >= 5 for h in roster) or
                any(int(e.get("lvl", 1)) >= 5 for e in graveyard)
            ):
                state["has_had_lvl5"] = True
            has_had_lvl3 = state.get("has_had_lvl3", False)
            has_had_lvl5 = state.get("has_had_lvl5", False)
            if has_had_lvl3 and state.get("gather_allies_done") and not state.get("family_business_done"):
                quests[2] = copy.deepcopy(BOSS_QUEST_FAMILY_BUSINESS)
            elif has_had_lvl5 and state.get("family_business_done") and not state.get("sins_of_the_father_done"):
                quests[2] = copy.deepcopy(BOSS_QUEST_SINS_OF_THE_FATHER)
        state["available_quests"] = quests
        save_state(state)

    if compact:
        lines = [
            f"  {i}. \033[1m{q['name']}\033[0m  Danger {q['danger']}  {q['length']}  {q['enemies']}"
            for i, q in enumerate(quests, start=1)
        ]
        return quests, lines

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
        types = [t.strip() for t in enemy_types.split("/")]
        lines.append(f"  Enemies: {enemy_types}")
        # Show quest duration (in seconds), adjusted for selected Fighters
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
        # Per-hero resistance tooltip
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
        lines.append(f"  {marker} {i}. {h['name']:<12} {h['class']:<8}  Lvl {h['lvl']}  HP {hp_pct}%{tip}")
    lines += [""]
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
    if s.get("quest_name") == "The Family Business":
        items = s.get("items", [])
        items.append("Signet Ring")
        s["items"] = items
        s["family_business_done"] = True
        rewards.append("Found: Signet Ring")
    if s.get("quest_name") == "Sins of the Father":
        items = s.get("items", [])
        items.append("Ancestral Skull")
        s["items"] = items
        s["sins_of_the_father_done"] = True
        rewards.append("Found: Ancestral Skull")
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
    quest_gold = _GOLD_FOR_DANGER.get(danger, 10) + _GOLD_FOR_LENGTH.get(length, 10)

    damage_taken: list[tuple[str, int, int]] = []
    fallen: list[str] = []
    mage_armor_map = s.get("mage_armor", {})
    now = time.time()
    for h in roster:
        if party_names is not None and h["name"] not in party_names:
            continue
        has_mage_armor = mage_armor_map.get(h["name"], 0) > now
        dmg = calc_damage(h.get("class", "Fighter"), enemy_types, danger, mage_armor=has_mage_armor)
        max_hp = float(h.get("max_hp", 100))
        hp_lost = max_hp * dmg
        h["hp"] = max(0.0, float(h.get("hp", max_hp)) - hp_lost)
        if h["hp"] == 0.0:
            fallen.append(h["name"])
            damage_taken.append((h["name"], int(dmg * 100), 0, None))
        else:
            old_lvl = int(h.get("lvl", 1))
            _award_exp(h, quest_exp)
            new_lvl = int(h.get("lvl", 1))
            leveled_to = new_lvl if new_lvl != old_lvl else None
            damage_taken.append((h["name"], int(dmg * 100), quest_exp, leveled_to))

    # Cleric: heal a random living party hero after combat
    living_party = [
        h for h in roster
        if h["name"] not in fallen
        and (party_names is None or h["name"] in party_names)
    ]
    # Cleric: each Cleric in the living party heals a random living hero
    cleric_rewards: list[str] = []
    for cleric in [h for h in living_party if h.get("class") == "Cleric"]:
        heal_pct = CLERIC_HEAL_PCT.get(int(cleric.get("lvl", 1)), 0.0)
        if heal_pct > 0 and living_party:
            target = random.choice(living_party)
            old_hp = float(target.get("hp", 0))
            max_hp_val = float(target.get("max_hp", 100))
            target["hp"] = min(max_hp_val, old_hp + max_hp_val * heal_pct)
            healed_pct = int((target["hp"] - old_hp) / max_hp_val * 100)
            if healed_pct > 0:
                target_desc = "themself" if target["name"] == cleric["name"] else target["name"]
                cleric_rewards.append(f"{cleric['name']} blessed {target_desc}: +{healed_pct}% HP restored")

    s["roster"] = [h for h in roster if h["name"] not in fallen]

    # Record fallen heroes in the graveyard
    if fallen:
        record_fallen(s, fallen, roster, quest_name, enemy_types)

    # Rogue bonus: sum gold bonuses from all Rogues in the living party
    total_rogue_pct = sum(
        ROGUE_GOLD_BONUS.get(int(h.get("lvl", 1)), 0.0)
        for h in living_party if h.get("class") == "Rogue"
    )
    if total_rogue_pct > 0:
        bonus = int(quest_gold * total_rogue_pct)
        quest_gold += bonus
        rewards_rogue = [f"Rogues swiped an extra {bonus}G ({int(total_rogue_pct * 100)}% bonus)"]
    else:
        rewards_rogue = []

    s["gold"] = int(s.get("gold", 0)) + quest_gold
    s["week"] = int(s.get("week", 0)) + 1

    rewards = _apply_scripted_rewards(s) + cleric_rewards + rewards_rogue
    rewards.append(f"Party earned {quest_gold}G")

    try:
        quest_end_time = float(s.get("quest_start", time.time())) + float(s.get("quest_duration", 0))
    except Exception:
        quest_end_time = time.time()

    for key in (
        "quest_start", "quest_id", "quest_name", "quest_danger",
        "quest_enemies", "quest_length", "quest_duration", "quest_party",
        "available_quests", "recruit_offers",
    ):
        s.pop(key, None)
    s["last_regen"] = quest_end_time
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
    # Fighter bonus: each Fighter's time reduction applies multiplicatively
    dur_multiplier = 1.0
    for h in party:
        if h.get("class") == "Fighter":
            reduction = FIGHTER_TIME_REDUCTION.get(int(h.get("lvl", 1)), 0.0)
            dur_multiplier *= (1.0 - reduction)
    if dur_multiplier < 1.0:
        dur = max(1, int(dur * dur_multiplier))
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
