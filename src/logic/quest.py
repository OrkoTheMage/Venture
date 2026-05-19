from __future__ import annotations
import copy
import random
import textwrap
import time
from pathlib import Path
from ..utils.state import load_state, save_state
from .events import apply_event_bonus, get_active_event, pick_next_event
from .combat import (
    calc_damage, exp_to_level, max_hp_for,
    RESIST,
)
from .classBonuses import FIGHTER_TIME_REDUCTION, CLERIC_HEAL_PCT, ROGUE_GOLD_BONUS
from .spells import (
    cast_wizard_spell,
    get_available_spells,
    get_casters_for_spell,
)
from .recruit import build_recruit_offers, hire_recruit
from .fallen import record_fallen
from .questDefinitions import (
    QUEST_LORE,
    render_lore,
    lore_line_count,
    LOCATION_QUESTS,
    LOCATION_BOSSES,
    INITIAL_QUEST,
    BOSS_QUEST_FAMILY_BUSINESS,
    BOSS_QUEST_SINS_OF_THE_FATHER,
    BOSS_QUEST_THIEVES_IN_THE_NIGHT,
)

# ── EXP constants ─────────────────────────────────────────────────────────── #
_EXP_FOR_LENGTH: dict[str, int] = {"Short": 20, "Medium": 30, "Long": 40}
_EXP_FOR_DANGER: dict[int, int] = {1: 10, 2: 20, 3: 30, 4: 40, 5: 50}

_GOLD_FOR_DANGER: dict[int, int] = {1: 10, 2: 20, 3: 40, 4: 80, 5: 160}
_GOLD_FOR_LENGTH: dict[str, int] = {"Short": 10, "Medium": 50, "Long": 100}

_QUEST_CARD_TPL = Path(__file__).parent.parent / "ascii" / "questCard.txt"
_ALLOWED_TYPES = ["Physical", "Magic", "Horror"]
_LENGTH_SECONDS = {"Short": 300, "Medium": 1800, "Long": 3600}


from ..utils.format import format_duration  # noqa: F401 — re-exported for callers

# ── Quest card rendering ─────────────────────────────────────────────────── #
# Fill in random enemy types for any quest that doesn't have one yet.
def _assign_enemies(quests: list[dict]) -> None:
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


# Substitute quest data into one quest card template.
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


def build_quest_cards(state: dict, compact: bool = False) -> tuple[list[dict], list[str]]:
    # Migrate: regenerate if cached quests pre-date the location system or event_quest flags
    if state.get("available_quests"):
        if any(not q.get("location") for q in state["available_quests"]):
            state.pop("available_quests")
    if state.get("available_quests"):
        active_event_loc = get_active_event(int(state.get("week", 0)), state).get("location")
        needs_regen = active_event_loc and not any(
            q.get("event_quest") for q in state["available_quests"]
            if q.get("location") == active_event_loc
        )
        if needs_regen:
            state.pop("available_quests")

    # Use persisted quests if already rolled; otherwise generate and save them
    if state.get("available_quests"):
        quests = state["available_quests"]
        changed = False
        if not any(q.get("length") == "Short" for q in quests if not q.get("boss")):
            # Force slot 1 Short (it is never a boss slot)
            quests[0]["length"] = "Short"
            changed = True
        for idx, q in enumerate(quests):
            if q.get("boss"):
                continue
            if idx == 0:
                min_d, max_d = 1, 2
            elif idx == 1:
                min_d, max_d = 2, 3
            else:
                min_d, max_d = 4, 5
            if int(q.get("danger", 1)) < min_d or int(q.get("danger", 1)) > max_d:
                q["danger"] = random.randint(min_d, max_d)
                changed = True
        if changed:
            state["available_quests"] = quests
            save_state(state)
    else:
        if not state.get("gather_allies_done"):
            quests = copy.deepcopy(INITIAL_QUEST)
        else:
            all_locations = list(LOCATION_QUESTS.keys())
            location_clears    = state.get("location_clears", {})
            location_boss_done = state.get("location_boss_done", {})

            # ── Boss queue ───────────────────────────────────────────────── #
            boss_queue = list(state.get("location_boss_queue", []))
            for loc in all_locations:
                if (
                    location_clears.get(loc, 0) >= 5
                    and not location_boss_done.get(loc, False)
                    and loc not in boss_queue
                ):
                    boss_queue.append(loc)
            state["location_boss_queue"] = boss_queue

            # ── Determine fixed boss slots ───────────────────────────────── #
            week       = int(state.get("week", 0))

            # Slot 1 (index 0): Thieves in the Night event quest
            slot1_quest = copy.deepcopy(BOSS_QUEST_THIEVES_IN_THE_NIGHT) if get_active_event(week, state).get("effect") == "thieves" else None
            if slot1_quest:
                slot1_quest["event_quest"] = True

            # Slot 2 (index 1): location boss
            slot2_quest = copy.deepcopy(LOCATION_BOSSES[boss_queue[0]]) if boss_queue else None

            # Slot 3 (index 2): estate milestone boss
            roster    = state.get("roster", [])
            graveyard = state.get("graveyard", [])
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

            slot3_quest = None
            if state.get("has_had_lvl3") and not state.get("family_business_done"):
                slot3_quest = copy.deepcopy(BOSS_QUEST_FAMILY_BUSINESS)
            elif state.get("has_had_lvl5") and state.get("family_business_done") and not state.get("sins_of_the_father_done"):
                slot3_quest = copy.deepcopy(BOSS_QUEST_SINS_OF_THE_FATHER)

            # ── Choose locations for free slots ──────────────────────────── #
            # Active event location must appear in at least one quest slot
            week       = int(state.get("week", 0))
            event_loc  = get_active_event(week, state)["location"]

            # Locations already occupied by boss quests (estate bosses use
            # "The Estate" which is not in LOCATION_QUESTS, so no conflict)
            boss_locs = set()
            if slot2_quest:
                boss_locs.add(slot2_quest["location"])

            free_count = (0 if slot1_quest else 1) + (0 if slot2_quest else 1) + (0 if slot3_quest else 1)
            available  = [l for l in all_locations if l not in boss_locs]

            if not event_loc or event_loc in boss_locs or free_count == 0:
                # Town event (no location), boss already covers it, or all slots filled
                free_locs = random.sample(available, free_count) if free_count > 0 else []
            else:
                # Event location must fill one of the free slots
                non_event = [l for l in available if l != event_loc]
                others    = random.sample(non_event, free_count - 1)
                free_locs = [event_loc] + others
                random.shuffle(free_locs)

            # ── Assemble quests ──────────────────────────────────────────── #
            slot_ranges = [(1, 2), (2, 3), (4, 5)]
            quests: list[dict] = []
            free_idx = 0

            for i in range(3):
                if i == 0 and slot1_quest:
                    quests.append(slot1_quest)
                elif i == 1 and slot2_quest:
                    quests.append(slot2_quest)
                elif i == 2 and slot3_quest:
                    quests.append(slot3_quest)
                else:
                    loc   = free_locs[free_idx]; free_idx += 1
                    q_def = random.choice(LOCATION_QUESTS[loc])
                    min_d, max_d = slot_ranges[i]
                    danger  = random.randint(min_d, max_d)
                    enemies = q_def["enemies"]
                    if "/" in enemies:
                        enemies = random.choice(enemies.split("/"))
                    quests.append({
                        "name":     q_def["name"],
                        "enemies":  enemies,
                        "danger":   danger,
                        "length":   random.choice(["Short", "Medium", "Long"]),
                        "location": loc,
                    })

            # Ensure at least one Short quest (boss slots are exempt)
            if not any(q.get("length") == "Short" for q in quests if not q.get("boss")):
                quests[0]["length"] = "Short"

            # Flag quests at the active event's location
            if event_loc:
                for q in quests:
                    if q.get("location") == event_loc:
                        q["event_quest"] = True

        state["available_quests"] = quests
        save_state(state)

    def _tag_str(q: dict, short: bool = False) -> str:
        parts = []
        if q.get("event_quest"):  parts.append("\033[32m[E]\033[0m" if short else "\033[32m[Event]\033[0m")
        if q.get("boss"):         parts.append("\033[31m[B]\033[0m" if short else "\033[31m[Boss]\033[0m")
        return (" ".join(parts) + " ") if parts else ""
    def _tag_w(q: dict, short: bool = False) -> int:
        w = 0
        if q.get("event_quest"):  w += len("[E] ") if short else len("[Event] ")
        if q.get("boss"):         w += len("[B] ") if short else len("[Boss] ")
        return w

    if compact:
        lines = ["", "  Available Quests:", ""]
        name_w    = max(len(q["name"]) + _tag_w(q, short=True) for q in quests)
        length_w  = max(len(q["length"])                      for q in quests)
        enemies_w = max(len(q["enemies"]) for q in quests)
        loc_w     = max(len(q.get("location", ""))            for q in quests)
        for i, q in enumerate(quests, start=1):
            loc       = q.get("location", "")
            enemies   = q["enemies"]
            event_tag = _tag_str(q, short=True)
            name_pad  = name_w - _tag_w(q, short=True)
            lines.append(
                f"  {i}.  {event_tag}\033[1m{q['name']:<{name_pad}}\033[0m"
                f"  \u2502  D{q['danger']}"
                f"  \u2502  {q['length']:<{length_w}}"
                f"  \u2502  {enemies:<{enemies_w}}"
                + (f"  \u2502  {loc:<{loc_w}}" if loc else "")
            )
        lines.append("")
        return quests, lines

    try:
        tpl = _QUEST_CARD_TPL.read_text()
        cards_text = ""
        for i, q in enumerate(quests, start=1):
            event_tag = _tag_str(q)
            cards_text += f" {i}. {event_tag}\n" + _render_quest_card(tpl, q) + "\n\n"
        return quests, cards_text.splitlines()
    except Exception:
        fallback = [
            _tag_str(q) + f"{i}. {q['name']} - Danger {q['danger']} - {q['length']} - {q['enemies']}"
            for i, q in enumerate(quests, start=1)
        ]
        return quests, fallback



# Add quest_exp to a hero and update their level and max_hp in-place.
def _award_exp(hero: dict, quest_exp: int) -> None:
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


# Apply scripted quest rewards to state. Returns reward description strings.
def _apply_scripted_rewards(s: dict) -> list[str]:
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
                rewards.append(f"\033[35m[Recruit]\033[0m {hero['name']} the {hero['class']} joins your roster")
        s["gather_allies_done"] = True
    if s.get("quest_name") == "The Family Business":
        items = s.get("items", [])
        items.append("Signet Ring")
        s["items"] = items
        s["family_business_done"] = True
        rewards.append("\033[35m[Relic]\033[0m Found: Signet Ring")
    if s.get("quest_name") == "Sins of the Father":
        items = s.get("items", [])
        items.append("Ancestral Skull")
        s["items"] = items
        s["sins_of_the_father_done"] = True
        rewards.append("\033[35m[Relic]\033[0m Found: Ancestral Skull")
    # Location boss rewards
    if s.get("quest_boss") and s.get("quest_location") in LOCATION_BOSSES:
        boss_def = LOCATION_BOSSES[s["quest_location"]]
        reward_item = boss_def.get("reward")
        if reward_item:
            items = s.get("items", [])
            items.append(reward_item)
            s["items"] = items
            rewards.append(f"\033[35m[Relic]\033[0m Found: {reward_item}")
        loc = s["quest_location"]
        lbd = s.get("location_boss_done", {})
        lbd[loc] = True
        s["location_boss_done"] = lbd
        # Pop from queue so the next queued boss can take slot 2
        boss_queue = s.get("location_boss_queue", [])
        if loc in boss_queue:
            boss_queue = [l for l in boss_queue if l != loc]
            s["location_boss_queue"] = boss_queue
    return rewards


# Apply damage to quest party on completion and clear quest keys.
# Returns a summary dict: {damage_taken: [(name, hp_pct_lost, exp_gained)], rewards: [str], fallen: [str]}.
def apply_quest_damage() -> dict:
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

    # Read The Bones: pre-determine one doomed hero and one spared hero
    active_event = get_active_event(0, s)
    bones_overrides: dict[str, float] = {}
    if active_event.get("effect") == "bones":
        _dl_ranges = {1: (0.01, 0.10), 2: (0.10, 0.20), 3: (0.20, 0.30), 4: (0.30, 0.40), 5: (0.40, 0.50)}
        _hi = _dl_ranges.get(danger, (0.01, 0.10))[1]
        party_names_for_bones = [
            h for h in roster
            if party_names is None or h["name"] in party_names
        ]
        if len(party_names_for_bones) >= 2:
            doomed_hero, spared_hero = random.sample(party_names_for_bones, 2)
            # Max damage = top of danger range with weakness modifiers, no nat-20 dodge
            _types = [t.strip() for t in enemy_types.split("/")]
            _cfg   = RESIST.get(doomed_hero.get("class", "Fighter"), {"resist": [], "weak": []})
            _mod   = 1.0
            for _t in _types:
                if _t in _cfg["weak"]:
                    _mod *= 1.50
            bones_overrides[doomed_hero["name"]] = min(1.0, _hi * _mod)
            bones_overrides[spared_hero["name"]] = 0.0
            s["_bones_doomed"] = doomed_hero["name"]
            s["_bones_spared"] = spared_hero["name"]
        elif len(party_names_for_bones) == 1:
            doomed_hero = party_names_for_bones[0]
            _types = [t.strip() for t in enemy_types.split("/")]
            _cfg   = RESIST.get(doomed_hero.get("class", "Fighter"), {"resist": [], "weak": []})
            _mod   = 1.0
            for _t in _types:
                if _t in _cfg["weak"]:
                    _mod *= 1.50
            bones_overrides[doomed_hero["name"]] = min(1.0, _hi * _mod)
            s["_bones_doomed"] = doomed_hero["name"]
            s["_bones_spared"] = None

    for h in roster:
        if party_names is not None and h["name"] not in party_names:
            continue
        has_mage_armor = mage_armor_map.get(h["name"], 0) > now
        dmg = bones_overrides.get(
            h["name"],
            calc_damage(h.get("class", "Fighter"), enemy_types, danger, mage_armor=has_mage_armor)
        )
        max_hp = float(h.get("max_hp", 100))
        hp_lost = max_hp * dmg
        h["hp"] = max(0.0, float(h.get("hp", max_hp)) - hp_lost)
        if h["hp"] == 0.0:
            fallen.append(h["name"])
            damage_taken.append((h["name"], int(dmg * 100), 0, None))
        else:
            old_lvl = int(h.get("lvl", 1))
            if old_lvl >= 5:
                damage_taken.append((h["name"], int(dmg * 100), 0, None))
            else:
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
                cleric_rewards.append(f"{cleric['name']} blessed {target_desc}: \033[32m+{healed_pct}% HP\033[0m restored")

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
        rewards_rogue = [f"Rogues swiped an extra \033[33m{bonus}G\033[0m ({int(total_rogue_pct * 100)}% bonus)"]
    else:
        rewards_rogue = []

    s["gold"] = int(s.get("gold", 0)) + quest_gold
    s["week"] = int(s.get("week", 0)) + 1

    rewards = _apply_scripted_rewards(s) + cleric_rewards + rewards_rogue
    rewards.append(f"Party earned \033[33m{quest_gold}G\033[0m")

    # ── Apply weekly event bonus (if quest location matches active event) ── #
    s["_event_gold_base"]   = quest_gold
    s["_event_exp_base"]    = quest_exp
    s["_event_fallen"]      = fallen
    s["_event_full_roster"] = roster
    event_rewards = apply_event_bonus(s, s.get("quest_location", ""), s.get("quest_party"))
    for key in ("_event_gold_base", "_event_exp_base", "_event_fallen", "_event_full_roster", "_bones_doomed", "_bones_spared"):
        s.pop(key, None)
    rewards += event_rewards

    # ── Thieves in the Night: penalty if the quest was not completed ───────── #
    _active_event = get_active_event(0, s)
    if _active_event.get("effect") == "thieves" and s.get("quest_name") != "Thieves in the Night":
        coffers = int(s.get("gold", 0))
        penalty = int(coffers * 0.5)
        s["gold"] = max(0, coffers - penalty)
        rewards.append(
            f"\033[31m[Thieves in the Night]\033[0m The thieves dissolved before the morning light"
            f" — \033[33m{penalty}G\033[0m was stolen"
        )

    # Advance to next event (never repeat last week's)
    pick_next_event(s)

    try:
        quest_end_time = float(s.get("quest_start", time.time())) + float(s.get("quest_duration", 0))
    except Exception:
        quest_end_time = time.time()

    # Track location clears
    quest_location = s.get("quest_location", "")
    if quest_location:
        lc = s.get("location_clears", {})
        lc[quest_location] = lc.get(quest_location, 0) + 1
        s["location_clears"] = lc

    # Decrement mage armor quest counts and remove expired entries
    mage_armor_map = s.get("mage_armor", {})
    for hero_name in list(mage_armor_map.keys()):
        remaining_quests = mage_armor_map[hero_name] - 1
        if remaining_quests <= 0:
            del mage_armor_map[hero_name]
        else:
            mage_armor_map[hero_name] = remaining_quests
    s["mage_armor"] = mage_armor_map

    # Clear portal flag if active
    s.pop("portal_active", None)

    for key in (
        "quest_start", "quest_id", "quest_name", "quest_danger",
        "quest_enemies", "quest_length", "quest_duration", "quest_party",
        "quest_location", "quest_boss",
        "available_quests", "recruit_offers",
    ):
        s.pop(key, None)

    s["last_regen"] = quest_end_time
    save_state(s)
    return {"damage_taken": damage_taken, "rewards": rewards, "fallen": fallen}



# ── Quest state ─────────────────────────────────────────────────────────── #

# Return timing info for the active quest, or {'running': False} if none.
def quest_info() -> dict:
    s = load_state()
    start = s.get("quest_start")
    if start is None:
        return {"running": False}
    try:
        start = float(start)
        duration = float(s.get("quest_duration", 60))
    except Exception:
        return {"running": False}
    # Portal spell: complete the quest instantly
    if s.get("portal_active"):
        return {
            "running": False,
            "elapsed": duration,
            "remaining": 0.0,
            "completed": True,
            "duration": duration,
        }
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


# ── Quest start ─────────────────────────────────────────────────────────── #

# Persist all quest keys into state and save.
def start_quest(state: dict, chosen: dict, party: list[dict]) -> None:
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
        "quest_location": chosen.get("location", ""),
        "quest_boss":     bool(chosen.get("boss", False)),
    })
    save_state(state)
