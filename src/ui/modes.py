from __future__ import annotations
import shlex
import time
from ..logic import combat, quest as quest_mod
from ..utils.state import load_state, save_state
from ..logic import heroes as roster_logic
from . import graveyard as graveyard_mod, journal as journal_mod, cards as cards_mod
from .party import build_party_screen, compact_heroes_per_page
from .roster import build_roster_lines
from .renderer import Renderer


# ── Roster ───────────────────────────────────────────────────────────────── #

def _show_roster(game: Renderer, page: int = 0) -> None:
    roster_logic.ensure_default_roster(game.state)
    lines = build_roster_lines(game.state, page, compact=game.compact)
    game.win.render(lines[:game.win.height])


# Returns True if the player wants to quit the game.
def enter_roster_mode(game: Renderer) -> bool:
    current_page = 0
    first_visit = not game.roster_seen
    _show_roster(game, current_page)
    if first_visit:
        print(
            "\nThis is your roster. In your service are Hadrik and Brynndar.\n"
            "Return to the main screen to embark on your first quest."
        )
    game.state["roster_seen"] = True
    save_state(game.state)
    game.roster_seen = True

    def _on_resize() -> None:
        game.apply_resize()
        _show_roster(game, current_page)
    game.win.on_resize = _on_resize

    while True:
        combat.apply_regen(game.state)
        try:
            raw = game.win.prompt(
                "roster> ", hint="Type a page number or 'help' for more commands, or press 'ENTER' to return"
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = raw.split()
        verb = parts[0].lower() if parts else ""
        # Page navigation: a bare digit navigates to that roster page
        if verb.isdigit():
            total = roster_logic.get_roster_page_count(game.state)
            p = int(verb) - 1
            if 0 <= p < total:
                current_page = p
                _show_roster(game, current_page)
            else:
                print(f"Invalid page. Enter 1-{total}.")
            continue
        result = roster_logic.handle_roster_command(verb, parts, game.state)
        if result == "quit":
            print("Goodbye!")
            return True
        if result == "back":
            return False
        if result == "list":
            _show_roster(game, current_page)


# ── Spells ───────────────────────────────────────────────────────────────── #

# Returns True if the player wants to quit.
def enter_spell_mode(game: Renderer) -> bool:
    # Block opening the spells view while a quest is active
    qi = quest_mod.quest_info()
    if qi.get("running"):
        lines = ["", "Cannot cast spells while a quest is in progress", ""]
        game.win.render(lines[:game.win.height])
        try:
            game.win.prompt("spells> ", hint="Press 'ENTER' to return").strip()
        except (EOFError, KeyboardInterrupt):
            pass
        return False

    def _show_spells(msg: str = "") -> None:
        lines = cards_mod.build_spell_card_lines(game.state, compact=game.compact)
        if msg:
            lines += ["", f"  {msg}"]
        game.win.render(lines[:game.win.height])

    _show_spells()

    def _on_resize() -> None:
        game.apply_resize()
        _show_spells()
    game.win.on_resize = _on_resize

    while True:
        combat.apply_regen(game.state)
        try:
            raw = game.win.prompt(
                "spells> ", hint="Type a number to cast, or press 'ENTER' to return"
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw or raw.lower() in ("back", "b"):
            return False
        if raw.lower() in ("quit", "exit"):
            print("Goodbye!")
            return True
        if not raw.isdigit():
            continue

        spells = quest_mod.get_available_spells(game.state)
        idx = int(raw) - 1
        if not (0 <= idx < len(spells)):
            print(f"Invalid choice. Enter 1-{len(spells)}.")
            continue
        chosen_spell = spells[idx]
        if not chosen_spell["can_cast"]:
            print(chosen_spell["reason"])
            continue

        # ── pick caster ───────────────────────────────────────────── #
        casters = quest_mod.get_casters_for_spell(game.state, chosen_spell["spell"])
        if len(casters) == 1:
            caster = casters[0]
        else:
            caster_lines = ["", f"Choose a caster for {chosen_spell['spell_label']}:"]
            for j, c in enumerate(casters, start=1):
                status = "(Ready)" if c["can_cast"] else f"({c['reason']})"
                caster_lines.append(f"  {j}. {c['wizard']} {status}")
            game.win.render(caster_lines[:game.win.height])
            try:
                c_raw = game.win.prompt(
                    "spells> ", hint="Choose a caster or press 'ENTER' to cancel"
                ).strip()
            except (EOFError, KeyboardInterrupt):
                c_raw = ""
            if not c_raw:
                _show_spells()
                continue
            if not c_raw.isdigit() or not (1 <= int(c_raw) <= len(casters)):
                print("Invalid choice.")
                _show_spells()
                continue
            caster = casters[int(c_raw) - 1]

        if not caster["can_cast"]:
            print(f"{caster['wizard']} cannot cast this spell: {caster['reason']}")
            _show_spells()
            continue

        # ── pick target (if needed) ───────────────────────────────── #
        target_name = None
        if chosen_spell["target"] in ("Other", "Any"):
            roster = game.state.get("roster", [])
            mage_armor_map = game.state.get("mage_armor", {})
            if chosen_spell["spell"] == "mage_armor":
                targets = [h for h in roster if mage_armor_map.get(h["name"], 0) <= 0]
            elif chosen_spell["spell"] == "inspire":
                from .combat import exp_to_level as _etl  # noqa: F401
                MAX_LVL = 5
                targets = [h for h in roster if int(h.get("lvl", 1)) < MAX_LVL]
            else:
                targets = roster
            if not targets:
                _show_spells("No valid targets available.")
                continue
            target_lines = ["", f"Choose a target for {chosen_spell['spell_label']}:"]
            for j, h in enumerate(targets, start=1):
                hp_pct = int(
                    float(h.get("hp", 100))
                    / max(1.0, float(h.get("max_hp", 100)))
                    * 100
                )
                target_lines.append(
                    f"  {j}. {h['name']} ({h['class']}, Lvl {h['lvl']}, HP {hp_pct}%)"
                )
            game.win.render(target_lines[:game.win.height])
            try:
                t_raw = game.win.prompt(
                    "spells> ", hint="Choose a target or press 'ENTER' to cancel"
                ).strip()
            except (EOFError, KeyboardInterrupt):
                t_raw = ""
            if not t_raw:
                _show_spells()
                continue
            if t_raw.isdigit():
                tidx = int(t_raw) - 1
                if 0 <= tidx < len(targets):
                    target_name = targets[tidx]["name"]
                else:
                    print("Invalid choice.")
                    _show_spells()
                    continue
            else:
                target_name = t_raw

        ok, msg = quest_mod.cast_wizard_spell(
            game.state, caster["wizard"], chosen_spell["spell"], target_name
        )
        game.state = load_state()
        _show_spells(msg)


# ── Recruit ──────────────────────────────────────────────────────────────── #

# Returns True if the player wants to quit.
def enter_recruit_mode(game: Renderer) -> bool:

    def _show_recruits() -> None:
        offers = quest_mod.build_recruit_offers(game.state)
        gold = int(game.state.get("gold", 0))
        lines = [f"  Gold: {gold}G"] + cards_mod.build_recruit_card_lines(
            offers, compact=game.compact
        )
        game.win.render(lines[:game.win.height])

    _show_recruits()

    def _on_resize() -> None:
        game.apply_resize()
        _show_recruits()
    game.win.on_resize = _on_resize

    while True:
        combat.apply_regen(game.state)
        try:
            raw = game.win.prompt(
                "recruit> ", hint="Type a number to hire, or press 'ENTER' to return"
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw or raw in ("back", "b"):
            return False
        if raw in ("quit", "exit"):
            print("Goodbye!")
            return True
        if raw.isdigit():
            idx = int(raw) - 1
            ok, msg = quest_mod.hire_recruit(game.state, idx)
            game.state = load_state()
            print(msg)
            if ok:
                _show_recruits()


# ── Quest / Party selection ───────────────────────────────────────────────── #

def select_party(
    game: Renderer,
    quest_name: str,
    max_party: int = 4,
    enemy_types: str = "",
    danger: int = 0,
    length: str = "Short",
    location: str = "",
) -> list | None:
    MAX_PARTY = max_party
    current_roster = game.state.get("roster", [])
    selected: list[int] = []
    hero_page = 0

    def _per_page() -> int:
        if not game.compact:
            return len(current_roster)
        return compact_heroes_per_page(quest_name, game.win.width, enemy_types, game.win.height)

    def _total_pages() -> int:
        import math
        return max(1, math.ceil(len(current_roster) / _per_page()))

    def _draw() -> None:
        lines = build_party_screen(
            quest_name, current_roster, selected, MAX_PARTY,
            game.win.width, enemy_types, danger, length,
            state=game.state, compact=game.compact,
            hero_page=hero_page,
            win_height=game.win.height if game.compact else None,
            location=location,
        )
        game.win.render(lines[:game.win.height])

    _draw()

    def _on_resize() -> None:
        game.apply_resize()
        _draw()
    game.win.on_resize = _on_resize

    while True:
        combat.apply_regen(game.state)
        try:
            raw = game.win.prompt(
                "quest> ",
                hint="Type a number to toggle, 'venture' to confirm, or press 'ENTER' to return",
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            raw = ""
        if not raw or raw in ("back", "b"):
            return None
        if raw in ("quit", "exit"):
            print("Goodbye!")
            return None
        if raw == "venture":
            if len(selected) != MAX_PARTY:
                print(f"You must select exactly {MAX_PARTY} heroes.")
                continue
            return [current_roster[i] for i in selected]
        if raw in ("n", "next") and game.compact:
            if hero_page < _total_pages() - 1:
                hero_page += 1
        elif raw in ("p", "prev") and game.compact:
            if hero_page > 0:
                hero_page -= 1
        elif raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(current_roster):
                if idx in selected:
                    selected.remove(idx)
                elif len(selected) < MAX_PARTY:
                    selected.append(idx)
                else:
                    print(f"Already have {MAX_PARTY} selected — deselect one first.")
                # Jump to the page that contains the toggled hero
                if game.compact:
                    hero_page = idx // _per_page()
            else:
                print(f"Invalid choice. Enter 1-{len(current_roster)}.")
        _draw()


# Returns True if the player wants to quit the game.
def enter_quest_mode(game: Renderer) -> bool:
    quests, card_lines = quest_mod.build_quest_cards(game.state, compact=game.compact)
    game.win.render(card_lines[:game.win.height])

    def _on_resize() -> None:
        nonlocal card_lines
        game.apply_resize()
        _, card_lines = quest_mod.build_quest_cards(game.state, compact=game.compact)
        game.win.render(card_lines[:game.win.height])
    game.win.on_resize = _on_resize

    while True:
        # Restore after select_party may have replaced win.on_resize.
        game.win.on_resize = _on_resize
        combat.apply_regen(game.state)
        try:
            choice = game.win.prompt(
                "quest> ", hint="Type a number to choose a quest or press 'ENTER' to return"
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        if not choice or choice in ("back", "b"):
            return False
        if choice in ("quit", "exit"):
            print("Goodbye!")
            return True
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(quests):
                chosen = quests[n - 1]
                chosen["_index"] = n
                enemies = chosen.get("enemies", "")
                danger = int(chosen.get("danger", 0))
                if chosen["name"] == "Gather Allies":
                    n_heroes = len(game.state.get("roster", []))
                    party = select_party(
                        game, chosen["name"], max_party=n_heroes,
                        enemy_types=enemies, danger=danger,
                        length=chosen.get("length", "Short"),
                        location=chosen.get("location", ""),
                    )
                else:
                    party = select_party(
                        game, chosen["name"], enemy_types=enemies,
                        danger=danger, length=chosen.get("length", "Short"),
                        location=chosen.get("location", ""),
                    )
                if party is None:
                    game.win.render(card_lines[:game.win.height])
                    continue
                quest_mod.start_quest(game.state, chosen, party)
                print(
                    f"Quest '{chosen['name']}' started — "
                    f"will complete in {quest_mod.format_duration(game.state['quest_duration'])} "
                    f"({chosen['length']})."
                )
                return False
        print(f"Please choose 1-{len(quests)}, 'back', or 'quit'.")


# ── Graveyard ────────────────────────────────────────────────────────────── #

# Returns True if the player wants to quit.
def enter_graveyard_mode(game: Renderer) -> bool:
    def _show() -> None:
        lines = graveyard_mod.build_graveyard_lines(game.state, compact=game.compact)
        game.win.render(lines[:game.win.height])

    _show()

    def _on_resize() -> None:
        game.apply_resize()
        _show()
    game.win.on_resize = _on_resize

    try:
        raw = game.win.prompt("graveyard> ", hint="Press 'ENTER' to return").strip()
    except (EOFError, KeyboardInterrupt):
        raw = ""

    if raw.lower() in ("quit", "exit"):
        print("Goodbye!")
        return True
    return False


# ── Journal ──────────────────────────────────────────────────────────────── #

# Returns True if the player wants to quit.
def enter_journal_mode(game: Renderer) -> bool:
    def _show() -> None:
        lines = journal_mod.build_journal_lines(game.state, compact=game.compact)
        game.win.render(lines[:game.win.height])

    _show()

    def _on_resize() -> None:
        game.apply_resize()
        _show()
    game.win.on_resize = _on_resize

    try:
        raw = game.win.prompt("journal> ", hint="Press 'ENTER' to return").strip()
    except (EOFError, KeyboardInterrupt):
        raw = ""

    if raw.lower() in ("quit", "exit"):
        print("Goodbye!")
        return True
    return False
